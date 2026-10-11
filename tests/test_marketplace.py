from decimal import Decimal
from django.test import TestCase, Client
from django.urls import reverse
from django.utils import timezone
import datetime

from apps.accounts.models import User
from apps.core.models import CompanySettings, ThemeSettings
from apps.tutors.models import TutorProfile, TutorSubject, TutorAvailability
from apps.parents.models import ParentProfile, StudentProfile
from apps.leads.models import TuitionRequirement, TutorMatch, LeadUnlock, LeadApplication
from apps.leads.matching import run_tutor_matching
from apps.leads.services import unlock_lead_for_tutor
from apps.billing.models import (
    CommissionRule, CommissionRecord, SubscriptionPlan, ContactCreditWallet, Invoice
)
from apps.billing.services import generate_commission_for_engagement
from apps.engagements.models import DemoClass, TuitionEngagement

class MarketplaceComprehensiveTestCase(TestCase):
    def setUp(self):
        # 1. Company & Theme Setup
        self.company = CompanySettings.get_settings()
        self.company.commission_enabled = True
        self.company.save()

        self.theme = ThemeSettings.get_settings()
        self.theme.primary_color = "#4f46e5"
        self.theme.save()

        # 2. Commission Rule (Model C - First Month 40%)
        self.comm_rule = CommissionRule.objects.create(
            rule_name="Standard First Month 40%",
            is_active=True,
            model_type=CommissionRule.ModelType.FIRST_MONTH,
            calculation_type=CommissionRule.CalculationType.PERCENTAGE,
            rate_percentage=Decimal('40.00'),
            minimum_commission=Decimal('500.00'),
            maximum_commission=Decimal('6000.00'),
            tax_percentage=Decimal('18.00')
        )

        # 3. Super Admin & Operations Staff
        self.admin_user = User.objects.create_superuser(
            username='admin_test', email='admin@test.com', password='password123', role=User.Role.SUPER_ADMIN
        )

        # 4. Tutor User & Profile
        self.tutor_user = User.objects.create_user(
            username='tutor_test', email='tutor@test.com', password='password123',
            first_name='Kiran', last_name='Rao', role=User.Role.TUTOR, phone_number='+91 99887 76655',
            city='Bengaluru', locality='Indiranagar'
        )
        self.tutor_profile = TutorProfile.objects.create(
            user=self.tutor_user,
            headline='Experienced Math and Physics Faculty',
            bio='B.Tech with 8 years experience coaching high school CBSE & ICSE.',
            highest_qualification='B.Tech Electrical',
            primary_city='Bengaluru',
            primary_locality='Indiranagar',
            teaching_mode=TutorProfile.TeachingMode.BOTH_HOME_ONLINE,
            monthly_rate_estimate=Decimal('6000.00'),
            verification_status=TutorProfile.VerificationStatus.VERIFIED
        )
        TutorSubject.objects.create(
            tutor=self.tutor_profile,
            subject_name='Mathematics',
            classes_offered='Class 9-10, Class 11-12',
            fee_per_month=Decimal('6000.00')
        )
        TutorSubject.objects.create(
            tutor=self.tutor_profile,
            subject_name='Physics',
            classes_offered='Class 10, Class 11-12',
            fee_per_month=Decimal('5500.00')
        )

        # Wallet with 5 credits
        self.wallet = ContactCreditWallet.get_or_create_wallet(self.tutor_profile)
        self.wallet.free_credits = 2
        self.wallet.purchased_credits = 3
        self.wallet.save()

        # 5. Parent User & Profile
        self.parent_user = User.objects.create_user(
            username='parent_test', email='parent@test.com', password='password123',
            first_name='Sunita', last_name='Patel', role=User.Role.PARENT, phone_number='+91 98450 54321',
            city='Bengaluru', locality='Indiranagar'
        )
        self.parent_profile = ParentProfile.objects.create(
            user=self.parent_user,
            city='Bengaluru',
            locality='Indiranagar',
            address_line='12th Main Road, Indiranagar, Bengaluru'
        )
        self.student_profile = StudentProfile.objects.create(
            parent=self.parent_profile,
            student_name='Rohan Patel',
            grade_level='Class 10',
            board_curriculum='CBSE'
        )

        # 6. Tuition Requirement (Lead)
        self.lead = TuitionRequirement.objects.create(
            parent=self.parent_profile,
            student=self.student_profile,
            title='Class 10 CBSE Mathematics Tutor Needed in Indiranagar',
            student_class='Class 10',
            board_curriculum='CBSE',
            subjects='Mathematics, Physics',
            tuition_type=TuitionRequirement.TuitionType.HOME_TUITION,
            city='Bengaluru',
            locality='Indiranagar',
            budget_amount=Decimal('6000.00'),
            parent_contact_name='Sunita Patel',
            contact_phone='+91 98450 54321',
            contact_email='sunita.patel@gmail.com',
            full_address='12th Main Road, Indiranagar, Bengaluru',
            credits_to_unlock=1,
            status=TuitionRequirement.Status.OPEN
        )

    def test_tutor_matching_engine(self):
        """Tests that the weighted matching engine calculates accurate scores and reasons."""
        matches = run_tutor_matching(self.lead)
        self.assertGreater(len(matches), 0)
        top_match = matches[0]
        self.assertEqual(top_match.tutor, self.tutor_profile)
        self.assertGreaterEqual(top_match.match_score, 80)
        self.assertIn("Specialized in", top_match.match_reasons)
        self.assertIn("Indiranagar", top_match.match_reasons)

    def test_contact_privacy_and_lead_unlock(self):
        """Tests atomic lead unlocking, credit deduction, and contact privacy."""
        self.assertEqual(self.wallet.total_balance, 5)
        self.assertFalse(self.lead.is_unlocked_by(self.tutor_profile))

        success, msg, data = unlock_lead_for_tutor(self.lead, self.tutor_profile)
        self.assertTrue(success)
        self.assertEqual(data['contact_phone'], '+91 98450 54321')
        self.assertEqual(data['parent_contact_name'], 'Sunita Patel')

        # Check credit balance deducted by 1
        self.wallet.refresh_from_db()
        self.assertEqual(self.wallet.total_balance, 4)

        # Double unlock attempt must not charge again
        success2, msg2, data2 = unlock_lead_for_tutor(self.lead, self.tutor_profile)
        self.assertTrue(success2)
        self.assertTrue(data2.get('already_unlocked'))
        self.wallet.refresh_from_db()
        self.assertEqual(self.wallet.total_balance, 4)

    def test_commission_calculation_when_enabled(self):
        """Tests commission engine calculation when enabled (Model C - 40% first month)."""
        engagement = TuitionEngagement.objects.create(
            requirement=self.lead,
            tutor=self.tutor_profile,
            parent=self.parent_profile,
            student=self.student_profile,
            agreed_subjects='Mathematics & Physics',
            agreed_fee=Decimal('6000.00'),
            start_date=timezone.now().date(),
            status=TuitionEngagement.Status.ACTIVE
        )

        success, record, msg = generate_commission_for_engagement(engagement)
        self.assertTrue(success)
        self.assertIsNotNone(record)

        # 40% of 6000 = 2400.00
        self.assertEqual(record.commission_amount, Decimal('2400.00'))
        # 18% tax on 2400 = 432.00
        self.assertEqual(record.tax_amount, Decimal('432.00'))
        # Total due = 2832.00
        self.assertEqual(record.total_amount, Decimal('2832.00'))
        self.assertEqual(record.status, CommissionRecord.Status.PENDING)

        # Check invoice generation
        invoice = Invoice.objects.filter(user=self.tutor_user, invoice_type=Invoice.InvoiceType.COMMISSION).first()
        self.assertIsNotNone(invoice)
        self.assertEqual(invoice.total_amount, Decimal('2832.00'))

    def test_commission_engine_when_disabled(self):
        """Tests that turning off commission disables calculation without creating records (Model A)."""
        self.company.commission_enabled = False
        self.company.save()

        engagement2 = TuitionEngagement.objects.create(
            requirement=self.lead,
            tutor=self.tutor_profile,
            parent=self.parent_profile,
            agreed_subjects='Mathematics',
            agreed_fee=Decimal('5000.00'),
            start_date=timezone.now().date(),
            status=TuitionEngagement.Status.ACTIVE
        )

        success, record, msg = generate_commission_for_engagement(engagement2)
        self.assertFalse(success)
        self.assertIsNone(record)
        self.assertIn("disabled", msg.lower())

    def test_demo_class_workflow(self):
        """Tests demo class creation and status transitions."""
        demo = DemoClass.objects.create(
            requirement=self.lead,
            tutor=self.tutor_profile,
            parent=self.parent_profile,
            scheduled_datetime=timezone.now() + datetime.timedelta(days=2),
            status=DemoClass.Status.REQUESTED
        )
        self.assertEqual(demo.status, DemoClass.Status.REQUESTED)

        demo.status = DemoClass.Status.COMPLETED
        demo.parent_feedback = "Excellent conceptual teaching."
        demo.attendance_confirmed_by_parent = True
        demo.save()

        self.assertEqual(demo.status, DemoClass.Status.COMPLETED)
        self.assertTrue(demo.attendance_confirmed_by_parent)

    def test_public_pages_and_custom_admin_access(self):
        """Tests web routes, public accessibility, and admin role enforcement."""
        client = Client()

        # Public pages
        resp_home = client.get(reverse('core:home'))
        self.assertEqual(resp_home.status_code, 200)
        self.assertContains(resp_home, "EduTutor Pro")

        resp_directory = client.get(reverse('tutors:directory'))
        self.assertEqual(resp_directory.status_code, 200)

        resp_board = client.get(reverse('leads:board'))
        self.assertEqual(resp_board.status_code, 200)

        # Anonymous access to admin portal must redirect
        resp_admin_anon = client.get(reverse('custom_admin:dashboard'))
        self.assertNotEqual(resp_admin_anon.status_code, 200)

        # Super admin access must succeed with code 200
        client.force_login(self.admin_user)
        resp_admin = client.get(reverse('custom_admin:dashboard'))
        self.assertEqual(resp_admin.status_code, 200)
        self.assertContains(resp_admin, "Executive Business Dashboard")

    def test_rest_api_endpoints_and_privacy(self):
        """Tests DRF public and authenticated endpoints and privacy controls."""
        client = Client()

        # Public Leads API - ensure phone & address are masked
        r_leads = client.get('/api/v1/leads/')
        self.assertEqual(r_leads.status_code, 200)
        data = r_leads.json()
        self.assertGreater(len(data), 0)
        # Verify contact_phone is NOT in public API response
        self.assertNotIn('contact_phone', data[0])
        self.assertNotIn('full_address', data[0])

        # Public Tutors API
        r_tutors = client.get('/api/v1/tutors/')
        self.assertEqual(r_tutors.status_code, 200)
        self.assertGreater(len(r_tutors.json()), 0)

        # Subscriptions API
        r_subs = client.get('/api/v1/subscriptions/')
        self.assertEqual(r_subs.status_code, 200)

        # Company Config API
        r_comp = client.get('/api/v1/company/')
        self.assertEqual(r_comp.status_code, 200)
        self.assertEqual(r_comp.json()['company_name'], 'EduTutor Pro')

