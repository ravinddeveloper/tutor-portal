import datetime
from decimal import Decimal
from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from django.utils import timezone

from apps.core.models import CompanySettings, ThemeSettings, Announcement
from apps.accounts.models import User
from apps.tutors.models import (
    TutorProfile, TutorQualification, TutorDocument, TutorSubject, TutorAvailability
)
from apps.parents.models import ParentProfile, StudentProfile
from apps.leads.models import TuitionRequirement, LeadApplication, LeadUnlock
from apps.leads.matching import run_tutor_matching
from apps.billing.models import (
    CommissionRule, CommissionRecord, SubscriptionPlan, TutorSubscription,
    ContactCreditWallet, CreditTransaction, Invoice, InvoiceLineItem, Payment
)
from apps.engagements.models import (
    DemoClass, TuitionEngagement, LessonSchedule, LessonRecord, StudentProgressReport, Review
)
from apps.communication.models import Notification, Conversation, Message

class Command(BaseCommand):
    help = 'Seeds realistic production-grade data for the Home Tuition Marketplace'

    def handle(self, *args, **options):
        self.stdout.write("Starting database seeding...")

        # 1. Company & Theme Settings
        company, _ = CompanySettings.objects.get_or_create(pk=1)
        company.company_name = "EduTutor Pro"
        company.tagline = "India's Most Trusted Home & Online Tuition Marketplace"
        company.support_email = "care@edututorpro.com"
        company.support_phone = "+91 98450 12345"
        company.whatsapp_number = "+91 98450 12345"
        company.office_address = "Level 3, Tech Park, Indiranagar 100ft Road, Bengaluru, Karnataka 560038"
        company.currency_symbol = "₹"
        company.currency_code = "INR"
        company.tax_percentage = Decimal('18.00')
        company.commission_enabled = True
        company.save()

        theme, _ = ThemeSettings.objects.get_or_create(pk=1)
        theme.theme_preset = "Modern Indigo"
        theme.primary_color = "#4f46e5"     # Indigo-600
        theme.secondary_color = "#06b6d4"   # Cyan-500
        theme.accent_color = "#f59e0b"      # Amber-500
        theme.background_color = "#f8fafc"  # Slate-50
        theme.surface_color = "#ffffff"
        theme.text_color = "#0f172a"
        theme.border_radius = "0.75rem"
        theme.save()

        # 2. Commission Rule (Model C - First Month 40%)
        comm_rule, _ = CommissionRule.objects.get_or_create(
            rule_name="Standard First-Month Commission",
            defaults={
                'is_active': True,
                'model_type': CommissionRule.ModelType.FIRST_MONTH,
                'calculation_type': CommissionRule.CalculationType.PERCENTAGE,
                'rate_percentage': Decimal('40.00'),
                'minimum_commission': Decimal('1000.00'),
                'maximum_commission': Decimal('8000.00'),
                'tax_percentage': Decimal('18.00'),
                'charged_to': 'TUTOR',
                'description': 'Charges 40% of the first month confirmed tuition fee.'
            }
        )

        # 3. Subscription Plans
        plans_data = [
            {
                'name': 'Starter Educator',
                'slug': 'starter-educator',
                'tagline': 'Ideal for individual tutors beginning their journey',
                'price': Decimal('499.00'),
                'duration_days': 30,
                'lead_credits_included': 5,
                'free_contact_unlocks': 3,
                'is_featured_badge': False,
                'priority_matching': False,
                'sort_order': 1
            },
            {
                'name': 'Gold Professional',
                'slug': 'gold-pro',
                'tagline': 'Our most popular plan with priority leads & verified badge boost',
                'price': Decimal('1299.00'),
                'duration_days': 60,
                'lead_credits_included': 18,
                'free_contact_unlocks': 10,
                'is_featured_badge': True,
                'priority_matching': True,
                'sort_order': 2
            },
            {
                'name': 'Platinum Master',
                'slug': 'platinum-master',
                'tagline': 'Unrestricted access, top directory ranking, and highest lead volume',
                'price': Decimal('2499.00'),
                'duration_days': 90,
                'lead_credits_included': 40,
                'free_contact_unlocks': 25,
                'is_featured_badge': True,
                'priority_matching': True,
                'sort_order': 3
            }
        ]
        created_plans = {}
        for p in plans_data:
            plan_obj, _ = SubscriptionPlan.objects.update_or_create(slug=p['slug'], defaults=p)
            created_plans[p['slug']] = plan_obj

        # 4. Core System Users
        # Super Admin
        admin_user, _ = User.objects.get_or_create(
            username='admin',
            defaults={
                'email': 'admin@edututorpro.com',
                'first_name': 'Ravi',
                'last_name': 'Director',
                'role': User.Role.SUPER_ADMIN,
                'is_staff': True,
                'is_superuser': True,
                'is_phone_verified': True,
                'is_email_verified': True,
                'phone_number': '+91 99000 11223',
                'city': 'Bengaluru'
            }
        )
        admin_user.set_password('admin123')
        admin_user.save()

        # Operations Manager
        ops_user, _ = User.objects.get_or_create(
            username='ops_manager',
            defaults={
                'email': 'operations@edututorpro.com',
                'first_name': 'Pooja',
                'last_name': 'Sharma',
                'role': User.Role.OPERATIONS,
                'is_staff': True,
                'is_phone_verified': True,
                'is_email_verified': True,
                'phone_number': '+91 98111 22334',
                'city': 'Bengaluru'
            }
        )
        ops_user.set_password('ops123')
        ops_user.save()

        # 5. Tutors Seeding
        tutors_seed = [
            {
                'username': 'tutor_rajesh',
                'first_name': 'Dr. Rajesh',
                'last_name': 'Nambiar',
                'email': 'rajesh.maths@edututorpro.com',
                'phone': '+91 98451 11222',
                'city': 'Bengaluru',
                'locality': 'Indiranagar',
                'headline': 'Senior IIT Faculty | 12+ Yrs Experience | CBSE & ICSE Mathematics Specialist',
                'bio': 'Ph.D. in Applied Mathematics with over a decade of experience preparing high school students for CBSE Class 10/12 board exams and JEE Mains. 95% of my students score above 90% in boards.',
                'gender': TutorProfile.Gender.MALE,
                'experience': 12,
                'highest_qualification': 'Ph.D. in Applied Mathematics',
                'institution': 'Indian Institute of Science (IISc), Bangalore',
                'teaching_mode': TutorProfile.TeachingMode.BOTH_HOME_ONLINE,
                'hourly_rate': Decimal('800.00'),
                'monthly_rate': Decimal('7500.00'),
                'languages': 'English, Hindi, Kannada',
                'verification_status': TutorProfile.VerificationStatus.VERIFIED,
                'is_featured': True,
                'rating': Decimal('4.95'),
                'reviews_count': 18,
                'subjects': [
                    ('Mathematics', 'Class 9-10, Class 11-12, JEE Foundation', 'CBSE, ICSE', Decimal('7500.00')),
                    ('Physics', 'Class 10, Class 11-12', 'CBSE, State Board', Decimal('7000.00')),
                ],
                'plan': 'platinum-master'
            },
            {
                'username': 'tutor_ananya',
                'first_name': 'Ananya',
                'last_name': 'Deshmukh',
                'email': 'ananya.biology@edututorpro.com',
                'phone': '+91 98200 33445',
                'city': 'Bengaluru',
                'locality': 'Koramangala',
                'headline': 'M.Sc Biochemistry | NEET Medical Exam Specialist | 7 Yrs Experience',
                'bio': 'Passionate educator focusing on concept clarity and visual memory techniques for NEET Biology and Class 11/12 Botany & Zoology. Mentored over 140 medical aspirants.',
                'gender': TutorProfile.Gender.FEMALE,
                'experience': 7,
                'highest_qualification': 'M.Sc Biochemistry',
                'institution': 'Delhi University',
                'teaching_mode': TutorProfile.TeachingMode.BOTH_HOME_ONLINE,
                'hourly_rate': Decimal('700.00'),
                'monthly_rate': Decimal('6500.00'),
                'languages': 'English, Hindi, Marathi',
                'verification_status': TutorProfile.VerificationStatus.VERIFIED,
                'is_featured': True,
                'rating': Decimal('4.90'),
                'reviews_count': 14,
                'subjects': [
                    ('Biology', 'Class 11-12, NEET Medical', 'CBSE, ICSE, State Board', Decimal('6500.00')),
                    ('Science', 'Class 8-10', 'CBSE, ICSE', Decimal('5500.00')),
                ],
                'plan': 'gold-pro'
            },
            {
                'username': 'tutor_vikram',
                'first_name': 'Vikram',
                'last_name': 'Sengupta',
                'email': 'vikram.physics@edututorpro.com',
                'phone': '+91 97111 44556',
                'city': 'Bengaluru',
                'locality': 'Whitefield',
                'headline': 'B.Tech IIT Kharagpur | Physics & Chemistry Mentor for ICSE & CBSE',
                'bio': 'Practical, problem-solving approach to Physics and Chemistry. I break down tough conceptual derivations into intuitive real-world examples.',
                'gender': TutorProfile.Gender.MALE,
                'experience': 6,
                'highest_qualification': 'B.Tech Electrical Engineering',
                'institution': 'IIT Kharagpur',
                'teaching_mode': TutorProfile.TeachingMode.HOME_ONLY,
                'hourly_rate': Decimal('600.00'),
                'monthly_rate': Decimal('6000.00'),
                'languages': 'English, Hindi, Bengali',
                'verification_status': TutorProfile.VerificationStatus.VERIFIED,
                'is_featured': False,
                'rating': Decimal('4.85'),
                'reviews_count': 9,
                'subjects': [
                    ('Physics', 'Class 9-10, Class 11-12', 'CBSE, ICSE', Decimal('6000.00')),
                    ('Chemistry', 'Class 9-10', 'CBSE, ICSE', Decimal('5000.00')),
                ],
                'plan': 'gold-pro'
            },
            {
                'username': 'tutor_priya',
                'first_name': 'Priya',
                'last_name': 'Menon',
                'email': 'priya.english@edututorpro.com',
                'phone': '+91 98452 77889',
                'city': 'Bengaluru',
                'locality': 'HSR Layout',
                'headline': 'M.A. English Literature & B.Ed | Primary & Middle School All Subjects',
                'bio': 'Patient, encouraging tutor specialized in building reading habits, grammatical precision, and general academic confidence for classes 1 through 8.',
                'gender': TutorProfile.Gender.FEMALE,
                'experience': 5,
                'highest_qualification': 'M.A. English & B.Ed',
                'institution': 'Christ University, Bangalore',
                'teaching_mode': TutorProfile.TeachingMode.HOME_ONLY,
                'hourly_rate': Decimal('500.00'),
                'monthly_rate': Decimal('4500.00'),
                'languages': 'English, Malayalam, Hindi',
                'verification_status': TutorProfile.VerificationStatus.VERIFIED,
                'is_featured': False,
                'rating': Decimal('4.88'),
                'reviews_count': 11,
                'subjects': [
                    ('English', 'Class 1-8, Class 9-10', 'CBSE, ICSE', Decimal('4500.00')),
                    ('Social Studies', 'Class 6-10', 'CBSE, ICSE', Decimal('4000.00')),
                    ('All Subjects', 'Class 1-5 Primary', 'All Boards', Decimal('5000.00')),
                ],
                'plan': 'starter-educator'
            },
            {
                'username': 'tutor_karthik',
                'first_name': 'Karthik',
                'last_name': 'Subramanian',
                'email': 'karthik.cs@edututorpro.com',
                'phone': '+91 98840 99001',
                'city': 'Bengaluru',
                'locality': 'Jayanagar',
                'headline': 'Software Architect & Python Trainer | Computer Science Class 11-12 & Coding',
                'bio': '10 years software industry experience, coaching high school students in Python, C++, SQL, and Informatics Practices.',
                'gender': TutorProfile.Gender.MALE,
                'experience': 8,
                'highest_qualification': 'M.Tech Computer Science',
                'institution': 'NIT Trichy',
                'teaching_mode': TutorProfile.TeachingMode.ONLINE_ONLY,
                'hourly_rate': Decimal('750.00'),
                'monthly_rate': Decimal('6000.00'),
                'languages': 'English, Tamil, Hindi',
                'verification_status': TutorProfile.VerificationStatus.VERIFIED,
                'is_featured': True,
                'rating': Decimal('4.92'),
                'reviews_count': 8,
                'subjects': [
                    ('Computer Science', 'Class 11-12, Python Programming', 'CBSE, ISC', Decimal('6000.00')),
                    ('Mathematics', 'Class 9-10', 'CBSE', Decimal('5500.00')),
                ],
                'plan': 'gold-pro'
            }
        ]

        tutor_profiles = []
        for tdata in tutors_seed:
            user, _ = User.objects.get_or_create(
                username=tdata['username'],
                defaults={
                    'email': tdata['email'],
                    'first_name': tdata['first_name'],
                    'last_name': tdata['last_name'],
                    'role': User.Role.TUTOR,
                    'phone_number': tdata['phone'],
                    'city': tdata['city'],
                    'locality': tdata['locality'],
                    'is_phone_verified': True,
                    'is_email_verified': True
                }
            )
            user.set_password('tutor123')
            user.save()

            tprofile, _ = TutorProfile.objects.update_or_create(
                user=user,
                defaults={
                    'headline': tdata['headline'],
                    'bio': tdata['bio'],
                    'gender': tdata['gender'],
                    'experience_years': tdata['experience'],
                    'highest_qualification': tdata['highest_qualification'],
                    'institution_name': tdata['institution'],
                    'teaching_mode': tdata['teaching_mode'],
                    'hourly_rate': tdata['hourly_rate'],
                    'monthly_rate_estimate': tdata['monthly_rate'],
                    'primary_city': tdata['city'],
                    'primary_locality': tdata['locality'],
                    'service_radius_km': 12,
                    'private_address': f"Flat 402, Royal Palms, {tdata['locality']}, {tdata['city']}",
                    'languages_spoken': tdata['languages'],
                    'verification_status': tdata['verification_status'],
                    'verified_at': timezone.now(),
                    'is_featured': tdata['is_featured'],
                    'profile_score': 95,
                    'average_rating': tdata['rating'],
                    'total_reviews': tdata['reviews_count'],
                    'total_completed_tuitions': tdata['reviews_count'] + 4
                }
            )

            # Subjects
            for sname, scls, scur, sfee in tdata['subjects']:
                TutorSubject.objects.update_or_create(
                    tutor=tprofile,
                    subject_name=sname,
                    defaults={
                        'classes_offered': scls,
                        'curriculum': scur,
                        'fee_per_month': sfee
                    }
                )

            # Availabilities (Mon to Sat evenings)
            for day_idx in range(6):
                TutorAvailability.objects.get_or_create(
                    tutor=tprofile,
                    day_of_week=day_idx,
                    slot=TutorAvailability.Slot.EVENING,
                    defaults={'is_active': True}
                )

            # Qualifications
            TutorQualification.objects.get_or_create(
                tutor=tprofile,
                degree_name=tdata['highest_qualification'],
                field_of_study="Academic Specialization",
                institution=tdata['institution'],
                defaults={'year_of_passing': 2018}
            )

            # Documents
            TutorDocument.objects.get_or_create(
                tutor=tprofile,
                document_type=TutorDocument.DocumentType.GOVT_ID,
                defaults={
                    'document_name': 'Govt Identity Verification (Aadhaar / Passport)',
                    'status': TutorDocument.Status.VERIFIED,
                    'verified_at': timezone.now()
                }
            )

            # Wallet & Credits
            wallet = ContactCreditWallet.get_or_create_wallet(tprofile)
            wallet.free_credits = 5
            wallet.purchased_credits = 20
            wallet.bonus_credits = 5
            wallet.save()

            # Subscription
            plan_obj = created_plans.get(tdata['plan'])
            if plan_obj:
                TutorSubscription.objects.get_or_create(
                    tutor=tprofile,
                    plan=plan_obj,
                    defaults={
                        'start_date': timezone.now().date(),
                        'end_date': timezone.now().date() + datetime.timedelta(days=plan_obj.duration_days),
                        'amount_paid': plan_obj.price,
                        'status': TutorSubscription.Status.ACTIVE
                    }
                )

            tutor_profiles.append(tprofile)

        # 6. Parents & Students Seeding
        parents_seed = [
            {
                'username': 'parent_meena',
                'first_name': 'Meena',
                'last_name': 'Iyer',
                'email': 'meena.iyer@gmail.com',
                'phone': '+91 98860 11998',
                'city': 'Bengaluru',
                'locality': 'Indiranagar',
                'address': '#42, 6th Cross, Indiranagar Stage 2, Bengaluru 560038',
                'student_name': 'Aditya Iyer',
                'grade': 'Class 10',
                'school': 'National Public School, Indiranagar',
                'board': 'CBSE'
            },
            {
                'username': 'parent_sanjay',
                'first_name': 'Sanjay',
                'last_name': 'Kapoor',
                'email': 'sanjay.kapoor@gmail.com',
                'phone': '+91 98201 55667',
                'city': 'Bengaluru',
                'locality': 'Koramangala',
                'address': '#115, 4th Block, Koramangala, Bengaluru 560034',
                'student_name': 'Rhea Kapoor',
                'grade': 'Class 12',
                'school': 'Bishop Cotton Girls School',
                'board': 'ICSE'
            },
            {
                'username': 'parent_anand',
                'first_name': 'Anand',
                'last_name': 'Verma',
                'email': 'anand.verma@yahoo.com',
                'phone': '+91 97412 88990',
                'city': 'Bengaluru',
                'locality': 'Whitefield',
                'address': 'Villa 18, Prestige Oasis, Whitefield, Bengaluru 560066',
                'student_name': 'Aryan Verma',
                'grade': 'Class 8',
                'school': 'The International School Bangalore (TISB)',
                'board': 'CBSE'
            }
        ]

        parent_profiles = []
        for pdata in parents_seed:
            puser, _ = User.objects.get_or_create(
                username=pdata['username'],
                defaults={
                    'email': pdata['email'],
                    'first_name': pdata['first_name'],
                    'last_name': pdata['last_name'],
                    'role': User.Role.PARENT,
                    'phone_number': pdata['phone'],
                    'city': pdata['city'],
                    'locality': pdata['locality'],
                    'is_phone_verified': True,
                    'is_email_verified': True
                }
            )
            puser.set_password('parent123')
            puser.save()

            parent_prof, _ = ParentProfile.objects.update_or_create(
                user=puser,
                defaults={
                    'address_line': pdata['address'],
                    'city': pdata['city'],
                    'locality': pdata['locality'],
                    'pincode': '560038'
                }
            )

            stud, _ = StudentProfile.objects.get_or_create(
                parent=parent_prof,
                student_name=pdata['student_name'],
                defaults={
                    'grade_level': pdata['grade'],
                    'school_or_college': pdata['school'],
                    'board_curriculum': pdata['board']
                }
            )
            parent_profiles.append((parent_prof, stud))

        # 7. Tuition Requirements / Leads (similar to HomeTutorSite reference)
        leads_seed = [
            {
                'parent_idx': 0, # Meena Iyer
                'lead_id': 'TUT-874167',
                'title': 'Home Tutor required for Class 10 CBSE Maths and Science in Indiranagar',
                'student_class': 'Class 10',
                'board': 'CBSE',
                'subjects': 'Mathematics, Physics',
                'tuition_type': TuitionRequirement.TuitionType.HOME_TUITION,
                'city': 'Bengaluru',
                'locality': 'Indiranagar',
                'landmark': 'Near BDA Complex 100ft Road',
                'days_per_week': 4,
                'preferred_timing': 'Evening (5:30 PM - 7:00 PM)',
                'budget': Decimal('7500.00'),
                'contact_phone': '+91 98860 11998',
                'contact_email': 'meena.iyer@gmail.com',
                'address': '#42, 6th Cross, Indiranagar Stage 2, Bengaluru',
                'learning_goals': 'Looking for an experienced faculty who can prepare student for 10th board exams. Focus on quadratic equations, trigonometry, and light electricity chapters.',
                'status': TuitionRequirement.Status.CONFIRMED
            },
            {
                'parent_idx': 1, # Sanjay Kapoor
                'lead_id': 'TUT-874290',
                'title': 'Online / Home Tutor for Class 12 Biology & Chemistry (NEET Prep)',
                'student_class': 'Class 12',
                'board': 'CBSE',
                'subjects': 'Biology, Chemistry',
                'tuition_type': TuitionRequirement.TuitionType.BOTH_HOME_ONLINE if hasattr(TuitionRequirement, 'BOTH_HOME_ONLINE') else TuitionRequirement.TuitionType.HOME_TUITION,
                'city': 'Bengaluru',
                'locality': 'Koramangala',
                'landmark': 'Sony World Junction',
                'days_per_week': 3,
                'preferred_timing': 'Evening (6:00 PM - 8:00 PM)',
                'budget': Decimal('7000.00'),
                'contact_phone': '+91 98201 55667',
                'contact_email': 'sanjay.kapoor@gmail.com',
                'address': '#115, 4th Block, Koramangala',
                'learning_goals': 'Student aiming for NEET Medical entrance. Needs rigorous practice tests and doubt solving.',
                'status': TuitionRequirement.Status.OPEN
            },
            {
                'parent_idx': 2, # Anand Verma
                'lead_id': 'TUT-874315',
                'title': 'Female Home Tutor for Class 8 All Subjects (ICSE Curriculum)',
                'student_class': 'Class 8',
                'board': 'ICSE',
                'subjects': 'English, Mathematics, Science',
                'tuition_type': TuitionRequirement.TuitionType.HOME_TUITION,
                'city': 'Bengaluru',
                'locality': 'Whitefield',
                'landmark': 'Near Hope Farm Junction',
                'days_per_week': 5,
                'preferred_timing': 'Evening (4:30 PM - 6:00 PM)',
                'budget': Decimal('6000.00'),
                'contact_phone': '+91 97412 88990',
                'contact_email': 'anand.verma@yahoo.com',
                'address': 'Villa 18, Prestige Oasis, Whitefield',
                'learning_goals': 'Daily homework support, concept clarity, and terminal exam preparations.',
                'status': TuitionRequirement.Status.OPEN
            }
        ]

        created_leads = []
        for ldata in leads_seed:
            parent_prof, student_prof = parent_profiles[ldata['parent_idx']]
            lead_obj, _ = TuitionRequirement.objects.update_or_create(
                lead_id=ldata['lead_id'],
                defaults={
                    'parent': parent_prof,
                    'student': student_prof,
                    'title': ldata['title'],
                    'student_class': ldata['student_class'],
                    'board_curriculum': ldata['board'],
                    'subjects': ldata['subjects'],
                    'tuition_type': ldata['tuition_type'],
                    'city': ldata['city'],
                    'locality': ldata['locality'],
                    'landmark': ldata['landmark'],
                    'days_per_week': ldata['days_per_week'],
                    'preferred_timing': ldata['preferred_timing'],
                    'budget_amount': ldata['budget'],
                    'parent_contact_name': parent_prof.display_name,
                    'contact_phone': ldata['contact_phone'],
                    'contact_email': ldata['contact_email'],
                    'full_address': ldata['address'],
                    'learning_goals': ldata['learning_goals'],
                    'credits_to_unlock': 1,
                    'status': ldata['status'],
                    'total_views': 35,
                    'total_unlocks': 3,
                    'total_applications': 2
                }
            )
            # Run intelligent matching engine on this lead!
            run_tutor_matching(lead_obj)
            created_leads.append(lead_obj)

        # 8. Unlocking & Applications on First Lead (TUT-874167)
        lead_1 = created_leads[0]
        rajesh_tutor = tutor_profiles[0]
        vikram_tutor = tutor_profiles[2]

        # Tutor Rajesh unlocked lead 1
        LeadUnlock.objects.get_or_create(
            requirement=lead_1,
            tutor=rajesh_tutor,
            defaults={
                'credits_spent': 1,
                'unlock_method': LeadUnlock.UnlockMethod.CREDIT_WALLET,
                'feedback_status': LeadUnlock.FeedbackStatus.VALID_CONTACT,
                'feedback_note': 'Connected with parent Meena Iyer. Scheduled a demo class on Tuesday.'
            }
        )

        # Tutor Rajesh applied
        LeadApplication.objects.get_or_create(
            requirement=lead_1,
            tutor=rajesh_tutor,
            defaults={
                'cover_note': 'I am the senior mathematics faculty at EduTutor Pro. I live in Indiranagar and have 12 years experience with CBSE Class 10.',
                'proposed_fee': Decimal('7500.00'),
                'status': LeadApplication.Status.ACCEPTED
            }
        )

        # Demo Class for Lead 1
        demo, _ = DemoClass.objects.get_or_create(
            requirement=lead_1,
            tutor=rajesh_tutor,
            parent=lead_1.parent,
            defaults={
                'mode': DemoClass.Mode.HOME,
                'scheduled_datetime': timezone.now() - datetime.timedelta(days=5),
                'duration_minutes': 60,
                'address': lead_1.full_address,
                'status': DemoClass.Status.COMPLETED,
                'tutor_notes': 'Demo went great. Tested Aditya on quadratic concepts and algebraic foundations.',
                'parent_feedback': 'Dr. Rajesh was extremely patient and structured. We are very happy to confirm.',
                'is_parent_satisfied': True,
                'attendance_confirmed_by_parent': True
            }
        )

        # 9. Confirmed Tuition Engagement
        engagement, _ = TuitionEngagement.objects.get_or_create(
            requirement=lead_1,
            tutor=rajesh_tutor,
            parent=lead_1.parent,
            defaults={
                'student': lead_1.student,
                'agreed_subjects': 'Class 10 CBSE Mathematics & Physics',
                'agreed_fee': Decimal('7500.00'),
                'billing_cycle': TuitionEngagement.BillingCycle.MONTHLY,
                'schedule_summary': 'Mon, Wed, Fri (5:30 PM - 7:00 PM)',
                'start_date': timezone.now().date() - datetime.timedelta(days=4),
                'status': TuitionEngagement.Status.ACTIVE,
                'total_classes_conducted': 3
            }
        )

        # 10. Lessons & Progress Records
        lesson_1, _ = LessonSchedule.objects.get_or_create(
            engagement=engagement,
            title='Class 1: Quadratic Equations Basics & Factorization',
            scheduled_datetime=timezone.now() - datetime.timedelta(days=3),
            defaults={
                'duration_minutes': 90,
                'status': LessonSchedule.Status.COMPLETED
            }
        )
        LessonRecord.objects.get_or_create(
            lesson=lesson_1,
            defaults={
                'attendance': LessonRecord.Attendance.PRESENT,
                'topics_covered': 'Standard form ax^2 + bx + c = 0, splitting middle term, roots derivation.',
                'homework_assigned': 'NCERT Exercise 4.1 & 4.2 all odd problems.',
                'tutor_remarks': 'Good conceptual grasp; needs practice in fast algebraic multiplication.',
                'parent_acknowledged': True
            }
        )

        StudentProgressReport.objects.get_or_create(
            engagement=engagement,
            report_title='Baseline Assessment & Foundation Review',
            report_period='October 2026',
            defaults={
                'topics_completed': 'Quadratic Equations, Coordinate Geometry review',
                'student_strengths': 'High engagement, quick at geometrical intuition',
                'areas_for_improvement': 'Calculation speed under timed exam conditions',
                'test_score_or_grade': '88% in Diagnostic Test',
                'recommendations': 'Continue 3 classes per week with weekend 30-min rapid quiz.'
            }
        )

        # Review
        Review.objects.get_or_create(
            tutor=rajesh_tutor,
            parent=lead_1.parent,
            defaults={
                'engagement': engagement,
                'rating': 5,
                'title': 'Outstanding teacher! Best math tutor in Indiranagar',
                'comment': 'Dr. Rajesh explains complex math chapters with absolute ease. My son has gained tremendous confidence in just two weeks.',
                'is_verified_booking': True,
                'is_approved': True
            }
        )

        # 11. Commission Calculation on Confirmed Engagement
        base_comm, tax_amt, total_comm = comm_rule.calculate_commission(Decimal('7500.00'))
        comm_rec, _ = CommissionRecord.objects.get_or_create(
            engagement=engagement,
            tutor=rajesh_tutor,
            requirement=lead_1,
            defaults={
                'rule_applied': comm_rule,
                'billing_period': 'First Month Commission (40%)',
                'base_tuition_fee': Decimal('7500.00'),
                'rate_applied': Decimal('40.00'),
                'commission_amount': base_comm,
                'tax_amount': tax_amt,
                'total_amount': total_comm,
                'status': CommissionRecord.Status.PAID,
                'paid_at': timezone.now()
            }
        )

        # Invoice & Payment for Commission
        inv, _ = Invoice.objects.get_or_create(
            user=rajesh_tutor.user,
            invoice_type=Invoice.InvoiceType.COMMISSION,
            defaults={
                'subtotal': base_comm,
                'tax_amount': tax_amt,
                'total_amount': total_comm,
                'status': Invoice.Status.PAID,
                'paid_at': timezone.now()
            }
        )
        InvoiceLineItem.objects.get_or_create(
            invoice=inv,
            description=f"First Month Service Commission - Engagement {engagement.engagement_id}",
            defaults={
                'quantity': 1,
                'unit_price': base_comm,
                'total_price': base_comm
            }
        )
        Payment.objects.get_or_create(
            invoice=inv,
            user=rajesh_tutor.user,
            defaults={
                'amount': total_comm,
                'method': Payment.Method.UPI,
                'gateway_reference': 'UPI-REF-9988776655',
                'status': Payment.Status.SUCCESSFUL
            }
        )

        # 12. Announcements
        Announcement.objects.get_or_create(
            title='Verified Home Tutors Needed for Board Exam Crash Batches (Indiranagar & Whitefield)',
            defaults={
                'content': 'Demand for CBSE Class 10 & 12 Science and Mathematics tutors has increased by 45% this month. Update your availability to receive instant lead broadcasts.',
                'badge_text': 'Tutor Opportunity',
                'target_role': Announcement.TargetRole.TUTOR,
                'priority': Announcement.Priority.HIGH,
                'target_city': 'Bengaluru',
                'is_published': True,
                'is_featured': True
            }
        )

        # 13. In-App Conversation & Chat
        chat, _ = Conversation.objects.get_or_create(
            user_a=rajesh_tutor.user,
            user_b=lead_1.parent.user,
            defaults={'requirement': lead_1}
        )
        Message.objects.get_or_create(
            conversation=chat,
            sender=lead_1.parent.user,
            body='Hello Dr. Rajesh, looking forward to starting classes for Aditya this week.',
            defaults={'is_read': True}
        )
        Message.objects.get_or_create(
            conversation=chat,
            sender=rajesh_tutor.user,
            body='Hello Mrs. Iyer! I will be visiting on Monday at 5:30 PM with the quadratic practice sheets.',
            defaults={'is_read': True}
        )

        self.stdout.write(self.style.SUCCESS("Database seeded successfully with realistic data!"))
        self.stdout.write(self.style.SUCCESS("Default credentials:"))
        self.stdout.write("  Super Admin: admin / admin123")
        self.stdout.write("  Operations: ops_manager / ops123")
        self.stdout.write("  Tutor: tutor_rajesh / tutor123")
        self.stdout.write("  Parent: parent_meena / parent123")
