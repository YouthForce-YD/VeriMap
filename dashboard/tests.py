from decimal import Decimal
from django.core.exceptions import ValidationError
from django.test import TestCase, Client
from django.urls import reverse

from accounts.models import User
from payments.models import Payment
from projects.models import Demand, ProjectProgress

class RegistrationTestCase(TestCase):
    def setUp(self):
        self.client = Client()

    def test_donor_registration_model_success(self):
        user = User(
            username='donor1@example.com',
            email='donor1@example.com',
            name='Donor One',
            phone_number='01712345678',
            national_id='1234567890',
            user_type='donor'
        )
        user.set_password('Secret123!')
        user.full_clean()
        user.save()

        self.assertEqual(user.user_type, 'donor')
        self.assertEqual(user.phone, '01712345678')
        self.assertEqual(user.phone_number, '01712345678')
        self.assertEqual(str(user), 'Donor One (Donor)')

    def test_receiver_registration_model_success(self):
        user = User(
            username='receiver1@example.com',
            email='receiver1@example.com',
            name='Receiver One',
            phone_number='01812345678',
            national_id='1234567890123',
            user_type='receiver'
        )
        user.set_password('Secret123!')
        user.full_clean()
        user.save()

        self.assertEqual(user.user_type, 'receiver')
        self.assertEqual(user.phone, '01812345678')
        self.assertEqual(str(user), 'Receiver One (Receiver)')

    def test_17_digit_nid_success(self):
        user = User(
            username='nid17@example.com',
            email='nid17@example.com',
            name='NID 17 User',
            phone_number='01912345678',
            national_id='12345678901234567',
            user_type='donor'
        )
        user.set_password('Secret123!')
        user.full_clean()
        user.save()
        self.assertEqual(user.national_id, '12345678901234567')

    def test_invalid_bangladeshi_phone_numbers(self):
        invalid_phones = [
            '12345',
            '01212345678',
            '0171234567',
            '017123456789',
            '02712345678',
            'abcdefghijk'
        ]
        for phone in invalid_phones:
            user = User(
                username=f'user_{phone}@example.com',
                email=f'user_{phone}@example.com',
                name='Invalid Phone User',
                phone_number=phone,
                national_id='1234567890',
                user_type='donor'
            )
            user.set_password('Secret123!')
            with self.assertRaises(ValidationError):
                user.full_clean()

    def test_invalid_nid_numbers(self):
        invalid_nids = [
            '12345',
            '123456789',
            '12345678901',
            '12345678901234',
            '123456789012345678',
            '123456789X'
        ]
        for nid in invalid_nids:
            user = User(
                username=f'user_{nid}@example.com',
                email=f'user_{nid}@example.com',
                name='Invalid NID User',
                phone_number='01712345678',
                national_id=nid,
                user_type='donor'
            )
            user.set_password('Secret123!')
            with self.assertRaises(ValidationError):
                user.full_clean()

    def test_registration_view_post_success(self):
        response = self.client.post(reverse('register'), {
            'name': 'Web Donor',
            'phone_number': '01612345678',
            'email': 'webdonor@example.com',
            'national_id': '9876543210',
            'address': 'Dhanmondi, Dhaka',
            'password': 'Password123!',
            'confirm_password': 'Password123!',
            'user_type': 'donor'
        })
        self.assertEqual(response.status_code, 302)
        self.assertTrue(User.objects.filter(email='webdonor@example.com').exists())

    def test_registration_view_post_invalid_phone(self):
        response = self.client.post(reverse('register'), {
            'name': 'Bad Phone Donor',
            'phone_number': '01112345678',
            'email': 'badphone@example.com',
            'national_id': '9876543210',
            'address': 'Dhaka',
            'password': 'Password123!',
            'confirm_password': 'Password123!',
            'user_type': 'donor'
        })
        self.assertEqual(response.status_code, 200)
        self.assertFalse(User.objects.filter(email='badphone@example.com').exists())

class DemandCreationTestCase(TestCase):
    def setUp(self):
        self.client = Client()
        self.receiver = User.objects.create_user(
            username='receiver_demand@example.com',
            email='receiver_demand@example.com',
            name='Receiver Demand',
            phone_number='01799887766',
            national_id='1122334455',
            user_type='receiver',
            password='Password123!'
        )

    def test_demand_donor_amount_calculation(self):
        demand = Demand(
            receiver=self.receiver,
            zilla='Dhaka',
            upozilla='Mirpur',
            detail_location='Section 10',
            demand_name='School Roof Repair',
            contact_no='01799887766',
            requested_amount=Decimal('10000.00'),
            problem_detail='Roof leaking during monsoon season.'
        )
        demand.clean()
        demand.save()

        self.assertEqual(demand.requested_amount, Decimal('10000.00'))
        self.assertEqual(demand.donor_amount, Decimal('11000.00'))
        self.assertEqual(demand.remaining_amount, Decimal('11000.00'))
        self.assertEqual(demand.collected_amount, Decimal('0.00'))

    def test_demand_minimum_requested_amount_validation(self):
        demand_low = Demand(
            receiver=self.receiver,
            zilla='Dhaka',
            upozilla='Mirpur',
            detail_location='Section 10',
            demand_name='Too Low Budget',
            contact_no='01799887766',
            requested_amount=Decimal('999.99'),
            problem_detail='Very small budget.'
        )
        with self.assertRaises(ValidationError):
            demand_low.full_clean()

        demand_valid = Demand(
            receiver=self.receiver,
            zilla='Dhaka',
            upozilla='Mirpur',
            detail_location='Section 10',
            demand_name='Valid Low Budget',
            contact_no='01799887766',
            requested_amount=Decimal('1000.00'),
            problem_detail='Minimum valid budget.'
        )
        demand_valid.full_clean()
        demand_valid.save()
        self.assertEqual(demand_valid.donor_amount, Decimal('1100.00'))

    def test_demand_maximum_requested_amount_validation(self):
        demand_high = Demand(
            receiver=self.receiver,
            zilla='Dhaka',
            upozilla='Mirpur',
            detail_location='Section 10',
            demand_name='Too High Budget',
            contact_no='01799887766',
            requested_amount=Decimal('50000000.01'),
            problem_detail='Very high budget.'
        )
        with self.assertRaises(ValidationError):
            demand_high.full_clean()

        demand_valid = Demand(
            receiver=self.receiver,
            zilla='Dhaka',
            upozilla='Mirpur',
            detail_location='Section 10',
            demand_name='Valid Max Budget',
            contact_no='01799887766',
            requested_amount=Decimal('50000000.00'),
            problem_detail='Maximum valid budget.'
        )
        demand_valid.full_clean()
        demand_valid.save()
        self.assertEqual(demand_valid.donor_amount, Decimal('55000000.00'))

    def test_receiver_dashboard_create_demand_post(self):
        self.client.login(username='receiver_demand@example.com', password='Password123!')
        response = self.client.post(reverse('receiver_dashboard'), {
            'zilla': 'Gazipur',
            'upozilla': 'Sreepur',
            'detail_location': 'Village Central',
            'demand_name': 'Solar Street Lights',
            'contact_no': '01799887766',
            'amount': '25000.00',
            'problem_detail': 'Dark roads causing security concerns.'
        })
        self.assertEqual(response.status_code, 302)

        created = Demand.objects.get(demand_name='Solar Street Lights')
        self.assertEqual(created.status, 'pending')
        self.assertEqual(created.requested_amount, Decimal('25000.00'))
        self.assertEqual(created.donor_amount, Decimal('27500.00'))
        self.assertEqual(created.remaining_amount, Decimal('27500.00'))

class AdminVerificationTestCase(TestCase):
    def setUp(self):
        self.client = Client()
        self.admin_user = User.objects.create_superuser(
            username='admin_test@example.com',
            email='admin_test@example.com',
            name='System Admin',
            phone_number='01711223344',
            password='AdminPassword123!'
        )
        self.receiver = User.objects.create_user(
            username='receiver_verif@example.com',
            email='receiver_verif@example.com',
            name='Receiver Verif',
            phone_number='01722334455',
            user_type='receiver',
            password='Password123!'
        )
        self.demand = Demand.objects.create(
            receiver=self.receiver,
            zilla='Sylhet',
            upozilla='Golapganj',
            detail_location='Bazar Road',
            demand_name='Community Well',
            contact_no='01722334455',
            requested_amount=Decimal('50000.00'),
            status='pending'
        )

    def test_admin_verifies_pending_demand(self):
        self.client.login(username='admin_test@example.com', password='AdminPassword123!')
        response = self.client.post(reverse('admin_dashboard'), {
            'form_type': 'demand_action',
            'demand_id': self.demand.id,
            'action': 'verify'
        })
        self.assertEqual(response.status_code, 302)

        self.demand.refresh_from_db()
        self.assertEqual(self.demand.status, 'verified')

    def test_admin_cancels_pending_demand(self):
        self.client.login(username='admin_test@example.com', password='AdminPassword123!')
        response = self.client.post(reverse('admin_dashboard'), {
            'form_type': 'demand_action',
            'demand_id': self.demand.id,
            'action': 'cancel'
        })
        self.assertEqual(response.status_code, 302)

        self.demand.refresh_from_db()
        self.assertEqual(self.demand.status, 'canceled')

    def test_non_admin_cannot_access_admin_dashboard(self):
        self.client.login(username='receiver_verif@example.com', password='Password123!')
        response = self.client.get(reverse('admin_dashboard'))
        self.assertEqual(response.status_code, 302)
        self.assertIn('/receiver/dashboard/', response.url)

class PaymentProcessingTestCase(TestCase):
    def setUp(self):
        self.client = Client()
        self.donor = User.objects.create_user(
            username='donor_pay@example.com',
            email='donor_pay@example.com',
            name='Generous Donor',
            phone_number='01733445566',
            user_type='donor',
            password='Password123!'
        )
        self.receiver = User.objects.create_user(
            username='receiver_pay@example.com',
            email='receiver_pay@example.com',
            name='Project Receiver',
            phone_number='01744556677',
            user_type='receiver',
            password='Password123!'
        )
        self.demand = Demand.objects.create(
            receiver=self.receiver,
            zilla='Bogura',
            upozilla='Sariakandi',
            detail_location='River Bank',
            demand_name='Flood Shelter Repair',
            contact_no='01744556677',
            requested_amount=Decimal('10000.00'),
            status='verified'
        )

    def test_partial_payment_updates_balance_and_retains_verified_status(self):
        self.client.login(username='donor_pay@example.com', password='Password123!')
        response = self.client.post(reverse('payment', args=[self.demand.id]), {
            'amount': '4000.00',
            'payment_method': 'bkash'
        })
        self.assertEqual(response.status_code, 302)

        self.demand.refresh_from_db()
        self.assertEqual(self.demand.collected_amount, Decimal('4000.00'))
        self.assertEqual(self.demand.remaining_amount, Decimal('7000.00'))
        self.assertEqual(self.demand.status, 'verified')

        payment = Payment.objects.get(demand=self.demand, donor=self.donor)
        self.assertEqual(payment.amount_paid, Decimal('4000.00'))
        self.assertEqual(payment.payment_status, 'success')
        self.assertTrue(payment.payment_gateway_ref.startswith('CB-'))

    def test_full_payment_transitions_demand_to_paid_and_initializes_progress(self):
        self.client.login(username='donor_pay@example.com', password='Password123!')
        response = self.client.post(reverse('payment', args=[self.demand.id]), {
            'amount': '11000.00',
            'payment_method': 'nagad'
        })
        self.assertEqual(response.status_code, 302)

        self.demand.refresh_from_db()
        self.assertEqual(self.demand.collected_amount, Decimal('11000.00'))
        self.assertEqual(self.demand.remaining_amount, Decimal('0.00'))
        self.assertEqual(self.demand.status, 'paid')

        progress = ProjectProgress.objects.get(demand=self.demand)
        self.assertEqual(progress.progress_percent, 0)

    def test_overpayment_rejected(self):
        self.client.login(username='donor_pay@example.com', password='Password123!')
        response = self.client.post(reverse('payment', args=[self.demand.id]), {
            'amount': '11500.00',
            'payment_method': 'rocket'
        })
        self.assertEqual(response.status_code, 200)

        self.demand.refresh_from_db()
        self.assertEqual(self.demand.collected_amount, Decimal('0.00'))
        self.assertEqual(Payment.objects.filter(demand=self.demand).count(), 0)

    def test_negative_or_zero_payment_rejected(self):
        self.client.login(username='donor_pay@example.com', password='Password123!')
        for invalid_amt in ['0.00', '-500.00', 'abc']:
            response = self.client.post(reverse('payment', args=[self.demand.id]), {
                'amount': invalid_amt,
                'payment_method': 'bkash'
            })
            self.assertEqual(response.status_code, 200)

        self.demand.refresh_from_db()
        self.assertEqual(self.demand.collected_amount, Decimal('0.00'))
        self.assertEqual(Payment.objects.filter(demand=self.demand).count(), 0)

    def test_sub_minimum_payment_rejected(self):
        self.client.login(username='donor_pay@example.com', password='Password123!')
        response = self.client.post(reverse('payment', args=[self.demand.id]), {
            'amount': '50.00',
            'payment_method': 'bkash'
        })
        self.assertEqual(response.status_code, 200)

        self.demand.refresh_from_db()
        self.assertEqual(self.demand.collected_amount, Decimal('0.00'))
        self.assertEqual(Payment.objects.filter(demand=self.demand).count(), 0)

    def test_payment_on_unverified_demand_returns_404(self):
        self.demand.status = 'pending'
        self.demand.save()

        self.client.login(username='donor_pay@example.com', password='Password123!')
        response = self.client.post(reverse('payment', args=[self.demand.id]), {
            'amount': '1000.00',
            'payment_method': 'bkash'
        })
        self.assertEqual(response.status_code, 404)

class ProjectProgressTestCase(TestCase):
    def setUp(self):
        self.client = Client()
        self.admin_user = User.objects.create_superuser(
            username='admin_prog@example.com',
            email='admin_prog@example.com',
            name='Admin Prog',
            phone_number='01755667788',
            password='AdminPassword123!'
        )
        self.receiver = User.objects.create_user(
            username='receiver_prog@example.com',
            email='receiver_prog@example.com',
            name='Receiver Prog',
            phone_number='01766778899',
            user_type='receiver',
            password='Password123!'
        )
        self.demand = Demand.objects.create(
            receiver=self.receiver,
            zilla='Khulna',
            upozilla='Rupsha',
            detail_location='Union Hospital',
            demand_name='Clinic Oxygen Plant',
            contact_no='01766778899',
            requested_amount=Decimal('50000.00'),
            collected_amount=Decimal('55000.00'),
            status='paid'
        )
        self.progress = ProjectProgress.objects.create(
            demand=self.demand,
            progress_percent=0
        )

    def test_progress_advance_to_100_marks_demand_completed(self):
        self.progress.progress_percent = 50
        self.progress.save()
        self.demand.refresh_from_db()
        self.assertEqual(self.demand.status, 'paid')

        self.progress.progress_percent = 100
        self.progress.save()
        self.demand.refresh_from_db()
        self.assertEqual(self.demand.status, 'completed')

    def test_reverting_progress_raises_validation_error(self):
        self.progress.progress_percent = 75
        self.progress.save()

        self.progress.progress_percent = 50
        with self.assertRaises(ValidationError):
            self.progress.full_clean()

    def test_reverting_completed_project_raises_validation_error(self):
        self.progress.progress_percent = 100
        self.progress.save()
        self.demand.refresh_from_db()
        self.assertEqual(self.demand.status, 'completed')

        self.progress.progress_percent = 75
        with self.assertRaises(ValidationError):
            self.progress.full_clean()

    def test_admin_dashboard_progress_post(self):
        self.client.login(username='admin_prog@example.com', password='AdminPassword123!')
        response = self.client.post(reverse('admin_dashboard'), {
            'form_type': 'update_progress',
            'demand_id': self.demand.id,
            'progress': '50',
            'update_note': 'Procurement complete and installation underway.'
        })
        self.assertEqual(response.status_code, 302)

        self.progress.refresh_from_db()
        self.assertEqual(self.progress.progress_percent, 50)
        self.assertEqual(self.progress.update_note, 'Procurement complete and installation underway.')

    def test_admin_dashboard_cannot_downgrade_progress(self):
        self.progress.progress_percent = 75
        self.progress.save()

        self.client.login(username='admin_prog@example.com', password='AdminPassword123!')
        response = self.client.post(reverse('admin_dashboard'), {
            'form_type': 'update_progress',
            'demand_id': self.demand.id,
            'progress': '25',
            'update_note': 'Attempted rollback.'
        })
        self.assertEqual(response.status_code, 302)

        self.progress.refresh_from_db()
        self.assertEqual(self.progress.progress_percent, 75)

class ReceiptPermissionTestCase(TestCase):
    def setUp(self):
        self.client = Client()
        self.donor1 = User.objects.create_user(
            username='donor1_receipt@example.com',
            email='donor1_receipt@example.com',
            name='Donor One',
            phone_number='01777889900',
            user_type='donor',
            password='Password123!'
        )
        self.donor2 = User.objects.create_user(
            username='donor2_receipt@example.com',
            email='donor2_receipt@example.com',
            name='Donor Two',
            phone_number='01788990011',
            user_type='donor',
            password='Password123!'
        )
        self.admin = User.objects.create_superuser(
            username='admin_receipt@example.com',
            email='admin_receipt@example.com',
            name='Receipt Admin',
            phone_number='01700112233',
            password='AdminPassword123!'
        )
        self.receiver = User.objects.create_user(
            username='receiver_receipt@example.com',
            email='receiver_receipt@example.com',
            name='Receiver Receipt',
            phone_number='01799001122',
            user_type='receiver',
            password='Password123!'
        )
        self.demand = Demand.objects.create(
            receiver=self.receiver,
            zilla='Rangpur',
            upozilla='Pirganj',
            detail_location='Union Parishad',
            demand_name='Winter Clothes Distribution',
            contact_no='01799001122',
            requested_amount=Decimal('20000.00'),
            status='verified'
        )
        self.payment = Payment.objects.create(
            demand=self.demand,
            donor=self.donor1,
            amount_paid=Decimal('5000.00'),
            payment_method='bkash',
            payment_status='success'
        )

    def test_donor_can_download_own_receipt(self):
        self.client.login(username='donor1_receipt@example.com', password='Password123!')
        response = self.client.get(reverse('download_receipt', args=[self.payment.id]))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response['Content-Type'], 'application/pdf')
        self.assertIn(f'Donation_Certificate_{self.payment.payment_gateway_ref}.pdf', response['Content-Disposition'])
        self.assertTrue(response.content.startswith(b'%PDF'))

    def test_other_donor_gets_404_when_accessing_foreign_receipt(self):
        self.client.login(username='donor2_receipt@example.com', password='Password123!')
        response = self.client.get(reverse('download_receipt', args=[self.payment.id]))
        self.assertEqual(response.status_code, 404)

    def test_admin_can_download_any_receipt(self):
        self.client.login(username='admin_receipt@example.com', password='AdminPassword123!')
        response = self.client.get(reverse('download_receipt', args=[self.payment.id]))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response['Content-Type'], 'application/pdf')
        self.assertTrue(response.content.startswith(b'%PDF'))

    def test_anonymous_user_redirected_to_login(self):
        response = self.client.get(reverse('download_receipt', args=[self.payment.id]))
        self.assertEqual(response.status_code, 302)
        self.assertIn(reverse('login'), response.url)
