import io
from decimal import Decimal
from PIL import Image, ImageDraw
from django.core.files.base import ContentFile
from django.core.management.base import BaseCommand
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from accounts.models import User
from payments.models import Payment
from projects.models import Demand, ProjectProgress


def generate_banner_png(title, location, badge_text, bg_hex):
    img = Image.new('RGB', (800, 450), color=bg_hex)
    draw = ImageDraw.Draw(img)
    draw.rectangle([24, 24, 776, 426], outline='#60A5FA', width=3)
    draw.rectangle([48, 48, 310, 92], fill='#10B981')
    draw.text((64, 62), badge_text.upper(), fill='#FFFFFF')
    draw.text((48, 140), "VERI MAP VERIFIED FIELD RECORD", fill='#93C5FD')
    if len(title) <= 45:
        draw.text((48, 185), title, fill='#FFFFFF')
    else:
        split_idx = title.rfind(' ', 0, 45)
        if split_idx == -1:
            split_idx = 45
        draw.text((48, 185), title[:split_idx].strip(), fill='#FFFFFF')
        draw.text((48, 215), title[split_idx:].strip(), fill='#FFFFFF')
    draw.text((48, 275), f"Location: {location}", fill='#CBD5E1')
    draw.text((48, 360), "Veri map Bangladesh - Verified Field Inspection", fill='#64748B')
    buf = io.BytesIO()
    img.save(buf, format='PNG')
    return buf.getvalue()


def generate_budget_pdf(title, location, amount):
    buf = io.BytesIO()
    p = canvas.Canvas(buf, pagesize=A4)
    width, height = A4
    p.setFillColor(colors.HexColor('#0F172A'))
    p.rect(0, height - 100, width, 100, fill=1, stroke=0)
    p.setFillColor(colors.white)
    p.setFont("Helvetica-Bold", 18)
    p.drawString(40, height - 55, "VERI MAP FIELD BUDGET ESTIMATE")
    p.setFont("Helvetica", 10)
    p.drawString(40, height - 75, "Verified Supporting Engineering & Community Cost Breakdown")
    p.setFillColor(colors.HexColor('#0F172A'))
    p.setFont("Helvetica-Bold", 13)
    p.drawString(40, height - 140, f"Project: {title}")
    p.setFont("Helvetica", 11)
    p.drawString(40, height - 162, f"Location: {location}")
    p.drawString(40, height - 184, f"Estimated Direct Community Budget: BDT {amount:,.2f}")
    p.drawString(40, height - 206, f"Total Target with 10% Service Fee: BDT {(amount * Decimal('1.10')):,.2f}")
    p.drawString(40, height - 245, "Status: Field Survey & Local Committee Approval Attached.")
    p.showPage()
    p.save()
    return buf.getvalue()


class Command(BaseCommand):
    help = 'Seed demo data with generated images and PDFs for client presentation'

    def handle(self, *args, **options):
        def sync_user(data):
            user = User.objects.filter(email=data['email']).first()
            if not user:
                user = User.objects.filter(username=data['username']).first()
            if not user and data.get('national_id'):
                user = User.objects.filter(national_id=data['national_id']).first()
            if not user and data.get('phone_number'):
                user = User.objects.filter(phone_number=data['phone_number']).first()
            if not user:
                user = User()
            for field, val in data.items():
                if field != 'password':
                    setattr(user, field, val)
            user.set_password(data['password'])
            user.save()
            return user

        admin_data = {
            'email': 'admin@communitybridge.bd',
            'username': 'admin',
            'name': 'System Administrator',
            'phone_number': '01711000000',
            'national_id': '1000000001',
            'address': 'Head Office, Dhaka',
            'user_type': 'admin',
            'is_staff': True,
            'is_superuser': True,
            'password': 'Admin@1234',
        }
        sync_user(admin_data)

        receivers_data = [
            {
                'email': 'rahim.bandarban@receiver.bd',
                'username': 'rahim_bandarban',
                'name': 'Abdur Rahim',
                'phone_number': '01811223344',
                'national_id': '1985123456789',
                'address': 'Hafezghona, Bandarban Sadar, Bandarban',
                'user_type': 'receiver',
                'is_staff': False,
                'is_superuser': False,
                'password': 'Pass@1234',
            },
            {
                'email': 'karim.sylhet@receiver.bd',
                'username': 'karim_sylhet',
                'name': 'Fazlul Karim',
                'phone_number': '01722334455',
                'national_id': '1990123456789',
                'address': 'Khadimnagar, Sylhet Sadar, Sylhet',
                'user_type': 'receiver',
                'is_staff': False,
                'is_superuser': False,
                'password': 'Pass@1234',
            },
            {
                'email': 'momena.kurigram@receiver.bd',
                'username': 'momena_kurigram',
                'name': 'Momena Begum',
                'phone_number': '01933445566',
                'national_id': '8234567890',
                'address': 'Rajarhat Road, Kurigram Sadar, Kurigram',
                'user_type': 'receiver',
                'is_staff': False,
                'is_superuser': False,
                'password': 'Pass@1234',
            },
        ]
        receivers = {r['email']: sync_user(r) for r in receivers_data}

        donors_data = [
            {
                'email': 'tanvir.ahmed@donor.bd',
                'username': 'tanvir_ahmed',
                'name': 'Tanvir Ahmed',
                'phone_number': '01611223344',
                'national_id': '5512345678',
                'address': 'Road 11, Gulshan-2, Dhaka',
                'user_type': 'donor',
                'is_staff': False,
                'is_superuser': False,
                'password': 'Pass@1234',
            },
            {
                'email': 'nusrat.jahan@donor.bd',
                'username': 'nusrat_jahan',
                'name': 'Dr. Nusrat Jahan',
                'phone_number': '01522334455',
                'national_id': '7712345678',
                'address': 'Dhanmondi 27, Dhaka',
                'user_type': 'donor',
                'is_staff': False,
                'is_superuser': False,
                'password': 'Pass@1234',
            },
            {
                'email': 'farhan.chowdhury@donor.bd',
                'username': 'farhan_chowdhury',
                'name': 'Farhan Chowdhury',
                'phone_number': '01333445566',
                'national_id': '1988123456789',
                'address': 'Agrabad C/A, Chattogram',
                'user_type': 'donor',
                'is_staff': False,
                'is_superuser': False,
                'password': 'Pass@1234',
            },
        ]
        donors = {d['email']: sync_user(d) for d in donors_data}

        demands_config = [
            {
                'slug': 'bandarban_water',
                'bg': '#0F172A',
                'receiver': receivers['rahim.bandarban@receiver.bd'],
                'zilla': 'Bandarban',
                'upozilla': 'Bandarban Sadar',
                'detail_location': 'Hafezghona, Ward 4, Bandarban Sadar',
                'demand_name': 'Solar Powered Deep Tube-Well for Hill Community',
                'problem_detail': 'Over 250 indigenous families in this hilly community face severe drinking water scarcity during dry seasons. Installing a solar-powered deep tube-well will provide continuous, safe drinking water.',
                'contact_no': '01811223344',
                'requested_amount': Decimal('80000.00'),
                'collected_amount': Decimal('0.00'),
                'status': 'pending',
                'payments': [],
                'progress': None,
            },
            {
                'slug': 'lama_bridge',
                'bg': '#1E3A8A',
                'receiver': receivers['rahim.bandarban@receiver.bd'],
                'zilla': 'Bandarban',
                'upozilla': 'Lama',
                'detail_location': 'Gajalia Union, Ward 2, Lama',
                'demand_name': 'Emergency Footbridge Repair for School Children',
                'problem_detail': 'The bamboo and timber footbridge was destroyed by heavy monsoon rainfall. Rebuilding it will restore safe access to school for over 120 primary school children.',
                'contact_no': '01811223344',
                'requested_amount': Decimal('50000.00'),
                'collected_amount': Decimal('0.00'),
                'status': 'verified',
                'payments': [],
                'progress': None,
            },
            {
                'slug': 'sunamganj_clinic',
                'bg': '#064E3B',
                'receiver': receivers['karim.sylhet@receiver.bd'],
                'zilla': 'Sunamganj',
                'upozilla': 'Sunamganj Sadar',
                'detail_location': 'Surma Union, Sunamganj Sadar',
                'demand_name': 'Flood Resilient Community Medical Clinic Renovation',
                'problem_detail': 'Recent flash floods damaged the community clinic roofing and medicine storage. Renovation and raising the plinth is urgently needed to resume local healthcare operations.',
                'contact_no': '01722334455',
                'requested_amount': Decimal('100000.00'),
                'collected_amount': Decimal('44000.00'),
                'status': 'verified',
                'payments': [
                    {
                        'donor': donors['tanvir.ahmed@donor.bd'],
                        'amount_paid': Decimal('44000.00'),
                        'payment_method': 'bkash',
                        'payment_gateway_ref': 'CB-SUNAM-001',
                        'payment_status': 'success',
                    }
                ],
                'progress': None,
            },
            {
                'slug': 'ctg_sewing',
                'bg': '#3B0764',
                'receiver': receivers['momena.kurigram@receiver.bd'],
                'zilla': 'Chattogram',
                'upozilla': 'Panchlaish',
                'detail_location': 'Muradpur, Ward 7, Panchlaish, Chattogram',
                'demand_name': 'Vocational Sewing Training Center for Underprivileged Women',
                'problem_detail': 'Setting up a community vocational training hub with 10 industrial sewing machines to train 40 women per batch for sustainable livelihoods.',
                'contact_no': '01933445566',
                'requested_amount': Decimal('120000.00'),
                'collected_amount': Decimal('132000.00'),
                'status': 'paid',
                'payments': [
                    {
                        'donor': donors['nusrat.jahan@donor.bd'],
                        'amount_paid': Decimal('80000.00'),
                        'payment_method': 'card',
                        'payment_gateway_ref': 'CB-CTG-001',
                        'payment_status': 'success',
                    },
                    {
                        'donor': donors['farhan.chowdhury@donor.bd'],
                        'amount_paid': Decimal('52000.00'),
                        'payment_method': 'nagad',
                        'payment_gateway_ref': 'CB-CTG-002',
                        'payment_status': 'success',
                    },
                ],
                'progress': {
                    'progress_percent': 50,
                    'update_note': 'Procured 10 sewing machines and completed electrical setup. Training classes commenced with 20 registered participants.',
                },
            },
            {
                'slug': 'dhaka_it',
                'bg': '#1E1B4B',
                'receiver': receivers['momena.kurigram@receiver.bd'],
                'zilla': 'Dhaka',
                'upozilla': 'Mirpur',
                'detail_location': 'Section 11, Block C, Mirpur, Dhaka',
                'demand_name': 'Community IT Center for Low-Income Youths',
                'problem_detail': 'Establishing an open digital lab with 8 computers, high-speed internet, and free basic computer programming courses for local youths.',
                'contact_no': '01933445566',
                'requested_amount': Decimal('150000.00'),
                'collected_amount': Decimal('165000.00'),
                'status': 'paid',
                'payments': [
                    {
                        'donor': donors['tanvir.ahmed@donor.bd'],
                        'amount_paid': Decimal('100000.00'),
                        'payment_method': 'rocket',
                        'payment_gateway_ref': 'CB-DHK-001',
                        'payment_status': 'success',
                    },
                    {
                        'donor': donors['nusrat.jahan@donor.bd'],
                        'amount_paid': Decimal('65000.00'),
                        'payment_method': 'bkash',
                        'payment_gateway_ref': 'CB-DHK-002',
                        'payment_status': 'success',
                    },
                ],
                'progress': {
                    'progress_percent': 75,
                    'update_note': 'Desktops and furniture installed, internet network configured, and initial batch of 25 students started digital skills curriculum.',
                },
            },
            {
                'slug': 'sylhet_water',
                'bg': '#065F46',
                'receiver': receivers['karim.sylhet@receiver.bd'],
                'zilla': 'Sylhet',
                'upozilla': 'Sylhet Sadar',
                'detail_location': 'Khadimnagar Union, Sylhet Sadar, Sylhet',
                'demand_name': 'Clean Drinking Water Filtration Plant for Rural School',
                'problem_detail': 'Installing a high-capacity reverse osmosis clean water purification plant serving 450 school students and 300 neighbouring residents.',
                'contact_no': '01722334455',
                'requested_amount': Decimal('70000.00'),
                'collected_amount': Decimal('77000.00'),
                'status': 'completed',
                'payments': [
                    {
                        'donor': donors['farhan.chowdhury@donor.bd'],
                        'amount_paid': Decimal('77000.00'),
                        'payment_method': 'bkash',
                        'payment_gateway_ref': 'CB-SYL-001',
                        'payment_status': 'success',
                    },
                ],
                'progress': {
                    'progress_percent': 100,
                    'update_note': 'Filtration plant installation fully completed, water quality tested and certified, and handed over to the school management committee.',
                },
            },
        ]

        for d_cfg in demands_config:
            demand = Demand.objects.filter(demand_name=d_cfg['demand_name']).first()
            if not demand:
                demand = Demand()
            demand.receiver = d_cfg['receiver']
            demand.zilla = d_cfg['zilla']
            demand.upozilla = d_cfg['upozilla']
            demand.detail_location = d_cfg['detail_location']
            demand.demand_name = d_cfg['demand_name']
            demand.problem_detail = d_cfg['problem_detail']
            demand.contact_no = d_cfg['contact_no']
            demand.requested_amount = d_cfg['requested_amount']
            demand.donor_amount = (d_cfg['requested_amount'] * Decimal('1.10')).quantize(Decimal('0.01'))
            demand.collected_amount = d_cfg['collected_amount']
            demand.status = d_cfg['status']

            png_bytes = generate_banner_png(
                d_cfg['demand_name'],
                f"{d_cfg['upozilla']}, {d_cfg['zilla']}",
                d_cfg['status'],
                d_cfg['bg']
            )
            if demand.problem_image:
                demand.problem_image.delete(save=False)
            demand.problem_image.save(f"{d_cfg['slug']}_field.png", ContentFile(png_bytes), save=False)

            pdf_bytes = generate_budget_pdf(
                d_cfg['demand_name'],
                f"{d_cfg['detail_location']}, {d_cfg['zilla']}",
                d_cfg['requested_amount']
            )
            if demand.supporting_document:
                demand.supporting_document.delete(save=False)
            demand.supporting_document.save(f"{d_cfg['slug']}_budget.pdf", ContentFile(pdf_bytes), save=False)

            demand.save()

            for p_cfg in d_cfg['payments']:
                payment = Payment.objects.filter(payment_gateway_ref=p_cfg['payment_gateway_ref']).first()
                if not payment:
                    payment = Payment(payment_gateway_ref=p_cfg['payment_gateway_ref'])
                payment.demand = demand
                payment.donor = p_cfg['donor']
                payment.amount_paid = p_cfg['amount_paid']
                payment.payment_method = p_cfg['payment_method']
                payment.payment_status = p_cfg['payment_status']
                payment.save()

            if d_cfg['progress']:
                prog = ProjectProgress.objects.filter(demand=demand).first()
                proof_bytes = generate_banner_png(
                    d_cfg['demand_name'],
                    f"{d_cfg['upozilla']}, {d_cfg['zilla']}",
                    f"MILESTONE {d_cfg['progress']['progress_percent']}% PROOF",
                    '#047857'
                )
                if prog:
                    ProjectProgress.objects.filter(pk=prog.pk).update(
                        progress_percent=d_cfg['progress']['progress_percent'],
                        update_note=d_cfg['progress']['update_note']
                    )
                    prog.refresh_from_db()
                    if prog.proof_image:
                        prog.proof_image.delete(save=False)
                    prog.proof_image.save(f"{d_cfg['slug']}_proof.png", ContentFile(proof_bytes), save=False)
                    ProjectProgress.objects.filter(pk=prog.pk).update(proof_image=prog.proof_image.name)
                else:
                    prog = ProjectProgress(
                        demand=demand,
                        progress_percent=d_cfg['progress']['progress_percent'],
                        update_note=d_cfg['progress']['update_note']
                    )
                    prog.proof_image.save(f"{d_cfg['slug']}_proof.png", ContentFile(proof_bytes), save=False)
                    prog.save()

            if d_cfg['status'] != demand.status:
                Demand.objects.filter(pk=demand.pk).update(status=d_cfg['status'])

        self.stdout.write(self.style.SUCCESS('Demo data with field photos and budget PDFs seeded successfully.'))
