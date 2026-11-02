import html
import io
import logging
from decimal import Decimal
from django.contrib import messages
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.password_validation import validate_password
from django.core.cache import cache
from django.core.exceptions import ValidationError
from django.db import transaction
from django.db.models import Sum
from django.http import Http404, HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from accounts.models import User
from payments.models import Payment
from projects.BD_DT import get_districts_by_division, get_upozillas
from projects.models import Demand, ProjectProgress, calculate_donor_target

logger = logging.getLogger(__name__)


def extract_validation_errors(exc):
    errors = {}
    if hasattr(exc, 'message_dict'):
        for field, msgs in exc.message_dict.items():
            clean_msgs = [str(m).strip("[]'") for m in msgs]
            errors[field] = ' '.join(clean_msgs)
    elif hasattr(exc, 'messages'):
        errors['__all__'] = ' '.join(str(m) for m in exc.messages)
    else:
        errors['__all__'] = 'Invalid input provided. Please check your entries.'
    return errors


def redirect_user_dashboard(user):
    if user.is_superuser or user.user_type == 'admin':
        return redirect('admin_dashboard')
    elif user.user_type == 'donor':
        return redirect('donor_dashboard')
    return redirect('receiver_dashboard')


def home_view(request):
    if request.user.is_authenticated and request.GET.get('preview') != '1':
        return redirect_user_dashboard(request.user)
    live_projects = Demand.objects.filter(status='verified').select_related('receiver')[:6]
    context = {
        'total_demands': Demand.objects.filter(status='verified').count(),
        'total_donors': User.objects.filter(user_type='donor', is_superuser=False).count(),
        'total_paid': Demand.objects.filter(status__in=['paid', 'completed']).count(),
        'live_projects': live_projects,
    }
    return render(request, 'public/index.html', context)


def login_view(request):
    if request.user.is_authenticated:
        return redirect_user_dashboard(request.user)
    login_tab = request.GET.get('tab', 'user')
    if login_tab not in ['user', 'admin']:
        login_tab = 'user'
    if request.method == 'POST':
        login_input = request.POST.get('login_input', '').strip()
        password = request.POST.get('password', '')
        login_tab = request.POST.get('login_tab', 'user').strip()
        if login_tab not in ['user', 'admin']:
            login_tab = 'user'

        client_ip = request.META.get('REMOTE_ADDR', 'unknown')
        rate_key = f"login_attempts_{client_ip}_{login_input.lower()}"
        attempts = cache.get(rate_key, 0)
        if attempts >= 5:
            messages.error(request, 'Too many failed login attempts. Please wait 1 minute before trying again.')
            return render(request, 'public/login.html', {'login_tab': login_tab, 'login_input': login_input})

        user_obj = User.objects.filter(email__iexact=login_input).first() or \
                   User.objects.filter(username__iexact=login_input).first()
        if user_obj:
            user = authenticate(request, username=user_obj.email, password=password)
            if user is not None:
                if login_tab == 'admin' and not (user.is_superuser or user.user_type == 'admin'):
                    messages.error(request, 'Access denied. You do not have administrator permissions.')
                    return render(request, 'public/login.html', {'login_tab': login_tab, 'login_input': login_input})
                cache.delete(rate_key)
                request.session.cycle_key()
                login(request, user)
                messages.success(request, f'Welcome back, {user.name}!')
                return redirect_user_dashboard(user)

        cache.set(rate_key, attempts + 1, 60)
        messages.error(request, 'Invalid email, username, or password. Please verify your credentials and try again.')
        return render(request, 'public/login.html', {'login_tab': login_tab, 'login_input': login_input})
    return render(request, 'public/login.html', {'login_tab': login_tab})


def register_view(request):
    if request.user.is_authenticated:
        return redirect_user_dashboard(request.user)
    reg_type = request.GET.get('type', 'donor')
    if reg_type not in ['donor', 'receiver']:
        reg_type = 'donor'
    if request.method == 'POST':
        name = request.POST.get('name', '').strip()
        phone = (request.POST.get('phone_number') or request.POST.get('phone', '')).strip()
        email = request.POST.get('email', '').strip().lower()
        national_id = request.POST.get('national_id', '').strip()
        address = request.POST.get('address', '').strip()
        password = request.POST.get('password', '')
        confirm = request.POST.get('confirm_password', '')
        user_type = request.POST.get('user_type', 'donor')
        if user_type not in ['donor', 'receiver']:
            user_type = 'donor'
        form_data = {
            'name': name,
            'phone_number': phone,
            'email': email,
            'national_id': national_id,
            'address': address,
            'user_type': user_type,
        }
        errors = {}
        if password != confirm:
            errors['confirm_password'] = 'Passwords do not match.'
        if len(password) < 6:
            errors['password'] = 'Password must be at least 6 characters long.'
        if User.objects.filter(email=email).exists():
            errors['email'] = 'This email is already registered. Please sign in.'
        if phone and User.objects.filter(phone_number=phone).exists():
            errors['phone_number'] = 'This mobile number is already registered.'
        if national_id and User.objects.filter(national_id=national_id).exists():
            errors['national_id'] = 'This National ID (NID) is already registered.'

        user = User(
            username=email,
            email=email,
            name=name,
            phone_number=phone,
            national_id=national_id or None,
            address=address,
            user_type=user_type,
        )
        if 'password' not in errors:
            try:
                validate_password(password, user=user)
            except ValidationError as pw_err:
                errors['password'] = ' '.join(pw_err.messages)

        if not errors:
            try:
                user.set_password(password)
                user.full_clean()
                user.save()
                messages.success(request, 'Account created successfully! Please sign in.')
                return redirect('login')
            except ValidationError as e:
                errors.update(extract_validation_errors(e))
            except Exception as e:
                logger.exception("Unexpected error during user registration")
                errors['__all__'] = 'An unexpected error occurred. Please check your information and try again.'
        messages.error(request, 'Please correct the errors indicated below.')
        return render(request, 'public/register.html', {
            'reg_type': user_type,
            'form_data': form_data,
            'errors': errors
        })
    return render(request, 'public/register.html', {'reg_type': reg_type})


def logout_view(request):
    logout(request)
    messages.info(request, 'You have been signed out safely.')
    return redirect('login')


def get_upozillas_api(request):
    district = request.GET.get('district', '').strip()
    upozillas = get_upozillas(district)
    return JsonResponse([{'name': u} for u in upozillas], safe=False)


@login_required
def receiver_dashboard(request):
    if request.user.user_type != 'receiver' and not request.user.is_superuser:
        return redirect_user_dashboard(request.user)
    form_data = {}
    errors = {}
    modal_open = False
    if request.method == 'POST':
        zilla = (request.POST.get('zilla_name') or request.POST.get('zilla', '')).strip()
        upozilla = request.POST.get('upozilla', '').strip()
        detail_loc = request.POST.get('detail_location', '').strip()
        demand_name = request.POST.get('demand_name', '').strip()
        contact_no = request.POST.get('contact_no', '').strip()
        amount = (request.POST.get('amount') or request.POST.get('requested_amount', '0')).strip()
        problem = (request.POST.get('problem_detail') or request.POST.get('problem', '')).strip()
        problem_image = request.FILES.get('problem_image')
        supporting_doc = request.FILES.get('supporting_document')
        form_data = {
            'zilla_name': zilla,
            'zilla': zilla,
            'upozilla': upozilla,
            'detail_location': detail_loc,
            'demand_name': demand_name,
            'contact_no': contact_no,
            'amount': amount,
            'requested_amount': amount,
            'problem_detail': problem,
        }
        if not zilla:
            errors['zilla_name'] = 'District is required.'
        if not upozilla:
            errors['upozilla'] = 'Upozilla is required.'
        req_amount = None
        donor_amount = None
        try:
            req_amount = Decimal(amount).quantize(Decimal('0.01'))
            donor_amount = calculate_donor_target(req_amount)
        except Exception:
            errors['amount'] = 'Please enter a valid numeric budget amount.'
        if not errors:
            try:
                demand = Demand(
                    receiver=request.user,
                    zilla=zilla,
                    upozilla=upozilla,
                    detail_location=detail_loc,
                    demand_name=demand_name,
                    contact_no=contact_no,
                    requested_amount=req_amount,
                    donor_amount=donor_amount,
                    problem_detail=problem,
                    problem_image=problem_image,
                    supporting_document=supporting_doc,
                    status='pending'
                )
                demand.full_clean()
                demand.save()
                messages.success(request, 'Project demand submitted! Awaiting admin verification.')
                return redirect('receiver_dashboard')
            except ValidationError as e:
                extracted = extract_validation_errors(e)
                if 'zilla' in extracted:
                    extracted['zilla_name'] = extracted['zilla']
                if 'requested_amount' in extracted:
                    extracted['amount'] = extracted['requested_amount']
                errors.update(extracted)
                modal_open = True
            except Exception:
                logger.exception("Unexpected error creating demand")
                errors['__all__'] = 'Could not save demand due to an unexpected error.'
                modal_open = True
        else:
            modal_open = True
        if errors:
            messages.error(request, 'Could not submit demand. Please correct the errors below.')
    tab = request.GET.get('tab', 'new')
    my_demands = Demand.objects.filter(receiver=request.user).select_related('progress')
    completed_all = my_demands.filter(status__in=['paid', 'completed'])
    context = {
        'tab': tab,
        'my_demands': my_demands,
        'completed_all': completed_all,
        'total_demands': my_demands.count(),
        'pending_count': my_demands.filter(status='pending').count(),
        'verified_count': my_demands.filter(status='verified').count(),
        'completed_count': completed_all.count(),
        'by_division': get_districts_by_division(),
        'form_data': form_data,
        'errors': errors,
        'modal_open': modal_open,
    }
    return render(request, 'dashboard/receiver.html', context)


@login_required
def donor_dashboard(request):
    if request.user.user_type != 'donor' and not request.user.is_superuser:
        return redirect_user_dashboard(request.user)
    tab = request.GET.get('tab', 'live')
    live_demands = Demand.objects.filter(status='verified').select_related('receiver')
    my_donations = Payment.objects.filter(
        donor=request.user, payment_status='success'
    ).select_related('demand', 'demand__receiver', 'demand__progress')
    total_paid_agg = my_donations.aggregate(total=Sum('amount_paid'))['total']
    if total_paid_agg is not None:
        total_paid = Decimal(str(total_paid_agg)).quantize(Decimal('0.01'))
    else:
        total_paid = Decimal('0.00')
    context = {
        'tab': tab,
        'live_demands': live_demands,
        'my_donations': my_donations,
        'live_count': live_demands.count(),
        'current_count': my_donations.count(),
        'total_paid': total_paid,
    }
    return render(request, 'dashboard/donor.html', context)


@login_required
def payment_view(request, demand_id):
    if request.user.user_type != 'donor' and not (request.user.is_superuser or request.user.user_type == 'admin'):
        return redirect_user_dashboard(request.user)

    demand = get_object_or_404(Demand, id=demand_id, status='verified')
    if request.method == 'POST':
        pay_amount_str = request.POST.get('amount', '').strip()
        payment_method = request.POST.get('payment_method', 'bkash').strip()
        try:
            with transaction.atomic():
                try:
                    pay_amount = Decimal(pay_amount_str).quantize(Decimal('0.01'))
                    if pay_amount <= Decimal('0.00'):
                        raise ValueError
                except Exception:
                    messages.error(request, 'Please provide a valid, positive payment amount.')
                    return render(request, 'dashboard/payment.html', {'demand': demand})
                locked_demand = Demand.objects.select_for_update().get(id=demand.id)
                if locked_demand.status != 'verified' or locked_demand.remaining_amount <= Decimal('0.00'):
                    messages.error(request, 'This project is no longer accepting donations.')
                    return redirect('/donor/dashboard/?tab=live')
                min_amount = min(Decimal('100.00'), locked_demand.remaining_amount)
                if pay_amount < min_amount:
                    messages.error(request, f'Payment amount must be at least BDT {min_amount:,.2f}.')
                    return render(request, 'dashboard/payment.html', {'demand': locked_demand})
                if pay_amount > locked_demand.remaining_amount:
                    messages.error(request, f'Payment amount cannot exceed remaining required amount of BDT {locked_demand.remaining_amount:,.2f}.')
                    return render(request, 'dashboard/payment.html', {'demand': locked_demand})
                payment = Payment(
                    demand=locked_demand,
                    donor=request.user,
                    amount_paid=pay_amount,
                    payment_method=payment_method,
                    payment_status='success'
                )
                payment.full_clean()
                payment.save()
                locked_demand.collected_amount = (locked_demand.collected_amount + pay_amount).quantize(Decimal('0.01'))
                if locked_demand.collected_amount >= locked_demand.donor_amount:
                    locked_demand.status = 'paid'
                    ProjectProgress.objects.get_or_create(
                        demand=locked_demand,
                        defaults={'progress_percent': 0}
                    )
                locked_demand.save()
            messages.success(
                request,
                f'Payment of BDT {pay_amount:,.2f} successful! Transaction Ref: {payment.payment_gateway_ref}'
            )
            return redirect('/donor/dashboard/?tab=current')
        except ValidationError as e:
            extracted = extract_validation_errors(e)
            messages.error(request, ' '.join(extracted.values()))
        except Exception:
            logger.exception("Unexpected payment processing error")
            messages.error(request, 'Payment could not be processed right now. Please try again.')
    return render(request, 'dashboard/payment.html', {'demand': demand})


@login_required
def download_donation_receipt(request, payment_id):
    payment = get_object_or_404(
        Payment.objects.select_related('demand', 'donor', 'demand__receiver'),
        id=payment_id
    )
    if not (request.user.is_superuser or request.user.user_type == 'admin' or payment.donor_id == request.user.id):
        raise Http404('Receipt not found.')

    safe_ref = html.escape(str(payment.payment_gateway_ref))
    safe_method = html.escape(str(payment.get_payment_method_display()))
    safe_status = html.escape(str(payment.get_payment_status_display()).upper())
    safe_donor_name = html.escape(str(payment.donor.name or payment.donor.username))
    safe_donor_email = html.escape(str(payment.donor.email))
    safe_donor_phone = html.escape(str(payment.donor.phone_number or payment.donor.phone or '—'))
    safe_project_name = html.escape(str(payment.demand.demand_name))
    safe_location = html.escape(f"{payment.demand.detail_location}, {payment.demand.upozilla}, {payment.demand.zilla}")
    safe_receiver_name = html.escape(str(payment.demand.receiver.name))

    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        rightMargin=36,
        leftMargin=36,
        topMargin=36,
        bottomMargin=36
    )
    styles = getSampleStyleSheet()
    header_style = ParagraphStyle(
        'CertHeader',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=24,
        leading=28,
        textColor=colors.HexColor('#1E3A8A'),
        alignment=1
    )
    sub_style = ParagraphStyle(
        'CertSub',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=12,
        leading=16,
        textColor=colors.HexColor('#0F172A'),
        alignment=1
    )
    tagline_style = ParagraphStyle(
        'CertTagline',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=9,
        leading=12,
        textColor=colors.HexColor('#64748B'),
        alignment=1
    )
    section_style = ParagraphStyle(
        'CertSection',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=12,
        leading=16,
        textColor=colors.HexColor('#1E3A8A')
    )
    label_style = ParagraphStyle(
        'CertLabel',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=9,
        leading=13,
        textColor=colors.HexColor('#475569')
    )
    val_style = ParagraphStyle(
        'CertVal',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=9,
        leading=13,
        textColor=colors.HexColor('#0F172A')
    )
    amount_title_style = ParagraphStyle(
        'CertAmountTitle',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=10,
        leading=14,
        textColor=colors.HexColor('#065F46'),
        alignment=1
    )
    amount_val_style = ParagraphStyle(
        'CertAmountVal',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=22,
        leading=26,
        textColor=colors.HexColor('#047857'),
        alignment=1
    )
    footer_text_style = ParagraphStyle(
        'CertFooter',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=8,
        leading=11,
        textColor=colors.HexColor('#64748B'),
        alignment=1
    )
    story = [
        Paragraph('VERI MAP', header_style),
        Spacer(1, 4),
        Paragraph('OFFICIAL DONATION CERTIFICATE &amp; RECEIPT', sub_style),
        Spacer(1, 2),
        Paragraph('Crowdfunding &amp; Community Impact Verification System', tagline_style),
        Spacer(1, 15)
    ]
    meta_data = [
        [
            Paragraph('Certificate Ref:', label_style),
            Paragraph(safe_ref, val_style),
            Paragraph('Payment Date:', label_style),
            Paragraph(payment.paid_at.strftime('%d %B %Y, %I:%M %p'), val_style)
        ],
        [
            Paragraph('Payment Method:', label_style),
            Paragraph(safe_method, val_style),
            Paragraph('Payment Status:', label_style),
            Paragraph(safe_status, val_style)
        ]
    ]
    t_meta = Table(meta_data, colWidths=[100, 160, 100, 163])
    t_meta.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor('#F8FAFC')),
        ('BOX', (0, 0), (-1, -1), 1, colors.HexColor('#CBD5E1')),
        ('INNERGRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#E2E8F0')),
        ('TOPPADDING', (0, 0), (-1, -1), 6),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
        ('LEFTPADDING', (0, 0), (-1, -1), 8),
        ('RIGHTPADDING', (0, 0), (-1, -1), 8),
    ]))
    story.append(t_meta)
    story.append(Spacer(1, 15))
    donor_data = [
        [Paragraph('DONOR INFORMATION', section_style), Paragraph('PROJECT &amp; BENEFICIARY DETAILS', section_style)],
        [
            Paragraph(f'<b>Name:</b> {safe_donor_name}', val_style),
            Paragraph(f'<b>Project:</b> {safe_project_name}', val_style)
        ],
        [
            Paragraph(f'<b>Email:</b> {safe_donor_email}', val_style),
            Paragraph(f'<b>Location:</b> {safe_location}', val_style)
        ],
        [
            Paragraph(f'<b>Contact:</b> {safe_donor_phone}', val_style),
            Paragraph(f'<b>Receiver:</b> {safe_receiver_name}', val_style)
        ],
        [
            Paragraph(f'<b>Donor Account ID:</b> #{payment.donor.id}', val_style),
            Paragraph(f'<b>Project Target:</b> {payment.demand.donor_amount:,.2f} BDT', val_style)
        ]
    ]
    t_details = Table(donor_data, colWidths=[261, 262])
    t_details.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#EEF2F6')),
        ('BACKGROUND', (0, 1), (-1, -1), colors.HexColor('#FFFFFF')),
        ('BOX', (0, 0), (-1, -1), 1, colors.HexColor('#CBD5E1')),
        ('INNERGRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#E2E8F0')),
        ('TOPPADDING', (0, 0), (-1, -1), 6),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
        ('LEFTPADDING', (0, 0), (-1, -1), 8),
        ('RIGHTPADDING', (0, 0), (-1, -1), 8),
    ]))
    story.append(t_details)
    story.append(Spacer(1, 15))
    amount_table_data = [
        [Paragraph('TOTAL AMOUNT DONATED', amount_title_style)],
        [Paragraph(f'{payment.amount_paid:,.2f} BDT', amount_val_style)]
    ]
    t_amount = Table(amount_table_data, colWidths=[523])
    t_amount.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor('#ECFDF5')),
        ('BOX', (0, 0), (-1, -1), 1.5, colors.HexColor('#10B981')),
        ('TOPPADDING', (0, 0), (-1, -1), 8),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
    ]))
    story.append(t_amount)
    story.append(Spacer(1, 20))
    story.append(Paragraph(
        'This official certificate acknowledges that the voluntary donation detailed above has been successfully received, verified, and allocated directly to the designated community initiative. Veri map certifies the transparency and traceability of this transaction.',
        footer_text_style
    ))
    story.append(Spacer(1, 10))
    story.append(Paragraph(
        'Veri map Foundation | Verified Digital Certificate | Generated automatically on ' + payment.paid_at.strftime('%Y-%m-%d'),
        footer_text_style
    ))
    doc.build(story)
    buffer.seek(0)
    response = HttpResponse(buffer.getvalue(), content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="Donation_Certificate_{payment.payment_gateway_ref}.pdf"'
    return response


@login_required
def admin_dashboard(request):
    if not (request.user.is_superuser or request.user.user_type == 'admin'):
        return redirect_user_dashboard(request.user)
    if request.method == 'POST':
        action_type = request.POST.get('form_type')
        if action_type == 'demand_action':
            demand = get_object_or_404(Demand, id=request.POST.get('demand_id'))
            act = request.POST.get('action')
            if act == 'verify':
                demand.status = 'verified'
                demand.save()
                messages.success(request, f'Project "{demand.demand_name}" has been verified!')
            elif act == 'cancel':
                demand.status = 'canceled'
                demand.save()
                messages.warning(request, f'Project "{demand.demand_name}" has been canceled.')
            return redirect('/admin-panel/?tab=demands')
        elif action_type == 'update_progress':
            demand = get_object_or_404(Demand, id=request.POST.get('demand_id'))
            pct = int(request.POST.get('progress', 0))
            note = request.POST.get('update_note', '').strip()
            proof_img = request.FILES.get('proof_image')
            prog_obj, _ = ProjectProgress.objects.get_or_create(demand=demand)
            try:
                prog_obj.progress_percent = pct
                if note:
                    prog_obj.update_note = note
                if proof_img:
                    prog_obj.proof_image = proof_img
                prog_obj.full_clean()
                prog_obj.save()
                messages.success(request, f'Progress for "{demand.demand_name}" updated to {pct}%!')
            except ValidationError as e:
                extracted = extract_validation_errors(e)
                messages.error(request, f"Progress update blocked: {' '.join(extracted.values())}")
            except Exception:
                logger.exception("Unexpected error updating project progress")
                messages.error(request, 'Progress update could not be saved.')
            return redirect('/admin-panel/?tab=current')
    tab = request.GET.get('tab', 'demands')
    status_filter = request.GET.get('status', 'all')
    demands_qs = Demand.objects.select_related('receiver', 'progress').all()
    if status_filter != 'all':
        demands_qs = demands_qs.filter(status=status_filter)
    donors = User.objects.filter(user_type='donor', is_superuser=False).prefetch_related('donations__demand')
    receivers = User.objects.filter(user_type='receiver').prefetch_related('demands')
    current_projects = Demand.objects.filter(
        status__in=['paid', 'completed']
    ).select_related('receiver', 'progress').prefetch_related('payments__donor')
    context = {
        'tab': tab,
        'status_filter': status_filter,
        'demands': demands_qs,
        'donors': donors,
        'receivers': receivers,
        'current_projects': current_projects,
        'total_donors': donors.count(),
        'total_receivers': receivers.count(),
        'pending_demands': Demand.objects.filter(status='pending').count(),
        'verified_demands': Demand.objects.filter(status='verified').count(),
        'ongoing_count': current_projects.count(),
    }
    return render(request, 'dashboard/admin.html', context)
