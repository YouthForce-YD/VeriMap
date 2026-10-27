from decimal import Decimal
from django.contrib import messages
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.db.models import Sum
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render

from accounts.models import User
from payments.models import Payment
from projects.BD_DT import get_districts_by_division, get_upozillas
from projects.models import Demand, ProjectProgress


# Create your views here.

def redirect_user_dashboard(user):
    if user.is_superuser or user.user_type == 'admin':
        return redirect('admin_dashboard')
    elif user.user_type == 'donor':
        return redirect('donor_dashboard')
    return redirect('receiver_dashboard')


def home_view(request):
    if request.user.is_authenticated:
        return redirect_user_dashboard(request.user)

    live_projects = Demand.objects.filter(status='verified').select_related('receiver')[:6]
    context = {
        'total_demands': Demand.objects.filter(status='verified').count(),
        'total_donors': User.objects.filter(user_type='donor').count(),
        'total_paid': Demand.objects.filter(status__in=['paid', 'completed']).count(),
        'live_projects': live_projects,
    }
    return render(request, 'public/index.html', context)

def login_view(request):
    if request.user.is_authenticated:
        return redirect_user_dashboard(request.user)

    if request.method == 'POST':
        login_input = request.POST.get('login_input', '').strip()
        password = request.POST.get('password', '')

        user_obj = User.objects.filter(email__iexact=login_input).first() or \
                   User.objects.filter(username__iexact=login_input).first()

        if user_obj:
            user = authenticate(request, username=user_obj.email, password=password)
            if user is not None:
                login(request, user)
                messages.success(request, f'Welcome back, {user.name}!')
                return redirect_user_dashboard(user)

        messages.error(request, 'Invalid email, username, or password.')

    return render(request, 'public/login.html')

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

        if password != confirm:
            messages.error(request, 'Passwords do not match.')
        elif len(password) < 6:
            messages.error(request, 'Password must be at least 6 characters long.')
        elif User.objects.filter(email=email).exists():
            messages.error(request, 'This email is already registered. Please sign in.')
        elif User.objects.filter(national_id=national_id).exists():
            messages.error(request, 'This National ID (NID) is already registered.')
        else:
            try:
                user = User(
                    username=email,
                    email=email,
                    name=name,
                    phone_number=phone,
                    national_id=national_id,
                    address=address,
                    user_type=user_type if user_type in ['donor', 'receiver'] else 'donor',
                )
                user.set_password(password)
                user.full_clean()
                user.save()
                messages.success(request, 'Account created successfully! Please sign in.')
                return redirect('login')
            except Exception as e:
                messages.error(request, f'Validation Error: {e}')

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

    if request.method == 'POST':
        zilla = request.POST.get('zilla_name', '').strip()
        upozilla = request.POST.get('upozilla', '').strip()
        detail_loc = request.POST.get('detail_location', '').strip()
        demand_name = request.POST.get('demand_name', '').strip()
        contact_no = request.POST.get('contact_no', '').strip()
        amount = request.POST.get('amount', '0')
        problem = request.POST.get('problem_detail', '').strip()
        problem_image = request.FILES.get('problem_image')
        supporting_doc = request.FILES.get('supporting_document')

        try:
            Demand.objects.create(
                receiver=request.user,
                zilla=zilla,
                upozilla=upozilla,
                detail_location=detail_loc,
                demand_name=demand_name,
                contact_no=contact_no,
                requested_amount=Decimal(amount),
                problem_detail=problem,
                problem_image=problem_image,
                supporting_document=supporting_doc,
                status='pending'
            )
            messages.success(request, 'Project demand submitted! Awaiting admin verification.')
        except Exception as e:
            messages.error(request, f'Could not submit demand: {e}')
        return redirect('receiver_dashboard')

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

    total_paid = my_donations.aggregate(total=Sum('amount_paid'))['total'] or Decimal('0.00')

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
    demand = get_object_or_404(Demand, id=demand_id, status='verified')

    if request.method == 'POST':
        pay_amount_str = request.POST.get('amount', str(demand.remaining_amount))
        payment_method = request.POST.get('payment_method', 'bkash')
        try:
            pay_amount = Decimal(pay_amount_str)
            if pay_amount <= 0 or pay_amount > demand.remaining_amount:
                pay_amount = demand.remaining_amount

            with transaction.atomic():
                locked_demand = Demand.objects.select_for_update().get(id=demand.id)
                payment = Payment.objects.create(
                    demand=locked_demand,
                    donor=request.user,
                    amount_paid=pay_amount,
                    payment_method=payment_method,
                    payment_status='success'
                )
                locked_demand.collected_amount += pay_amount
                if locked_demand.collected_amount >= locked_demand.donor_amount:
                    locked_demand.status = 'paid'
                    ProjectProgress.objects.get_or_create(demand=locked_demand, defaults={'progress_percent': 0})
                locked_demand.save()

            messages.success(
                request,
                f'Payment of ৳{pay_amount:,.2f} successful! Transaction Ref: {payment.payment_gateway_ref}'
            )
            return redirect('/donor/dashboard/?tab=current')
        except Exception as e:
            messages.error(request, f'Payment failed: {e}')

    return render(request, 'dashboard/payment.html', {'demand': demand})

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
            pct = int(request.POST.get('progress', 25))
            note = request.POST.get('update_note', '').strip()
            proof_img = request.FILES.get('proof_image')

            prog_obj, _ = ProjectProgress.objects.get_or_create(demand=demand)
            try:
                prog_obj.progress_percent = pct
                if note:
                    prog_obj.update_note = note
                if proof_img:
                    prog_obj.proof_image = proof_img
                prog_obj.save()
                messages.success(request, f'Progress for "{demand.demand_name}" updated to {pct}%!')
            except Exception as e:
                messages.error(request, f'Progress update blocked: {e}')
            return redirect('/admin-panel/?tab=current')

    tab = request.GET.get('tab', 'demands')
    status_filter = request.GET.get('status', 'all')

    demands_qs = Demand.objects.select_related('receiver', 'progress').all()
    if status_filter != 'all':
        demands_qs = demands_qs.filter(status=status_filter)

    donors = User.objects.filter(user_type='donor').prefetch_related('donations__demand')
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
