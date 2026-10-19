from django.test import TestCase, Client
from django.urls import reverse
from apps.accounts.models import User
from apps.tutors.models import (
    TutorProfile, TutorSubject, TutorQualification, TutorDocument, TutorAvailability, SavedTutor
)

class TutorCompletenessTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username='test_tutor',
            email='tutor@example.com',
            password='TestPassword123!',
            role=User.Role.TUTOR,
            first_name='Ananya',
            last_name='Sharma'
        )
        self.tutor = TutorProfile.objects.create(
            user=self.user,
            headline='',
            bio='',
            primary_city='Bengaluru',
            primary_locality='Koramangala'
        )

    def test_initial_completeness_score(self):
        comp = self.tutor.calculate_completeness()
        self.assertEqual(comp['score'], 0)
        self.assertFalse(comp['is_complete'])
        self.assertEqual(comp['remaining_count'], 5)

    def test_completeness_with_bio_and_headline(self):
        self.tutor.headline = 'Senior Math Educator'
        self.tutor.bio = 'Passionate about conceptual mathematics and calculus.'
        self.tutor.save()

        comp = self.tutor.calculate_completeness()
        self.assertEqual(comp['score'], 20)
        self.assertEqual(comp['remaining_count'], 4)

    def test_completeness_reaches_100_percent(self):
        self.tutor.headline = 'Senior Math Educator'
        self.tutor.bio = 'Passionate about conceptual mathematics.'
        self.tutor.save()

        TutorSubject.objects.create(
            tutor=self.tutor,
            subject_name='Mathematics',
            classes_offered='Class 11-12'
        )
        TutorQualification.objects.create(
            tutor=self.tutor,
            degree_name='M.Sc Mathematics',
            field_of_study='Pure Mathematics',
            institution='IISc'
        )
        TutorDocument.objects.create(
            tutor=self.tutor,
            document_type='GOVT_ID',
            document_name='Govt Aadhaar'
        )
        TutorAvailability.objects.create(
            tutor=self.tutor,
            day_of_week=TutorAvailability.DayOfWeek.MONDAY,
            slot=TutorAvailability.Slot.EVENING
        )

        comp = self.tutor.calculate_completeness()
        self.assertEqual(comp['score'], 100)
        self.assertTrue(comp['is_complete'])
        self.assertEqual(comp['remaining_count'], 0)


class SavedTutorTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.parent_user = User.objects.create_user(
            username='parent_user',
            email='parent@example.com',
            password='TestPassword123!',
            role=User.Role.PARENT
        )
        self.tutor_user = User.objects.create_user(
            username='tutor_user',
            email='tutor2@example.com',
            password='TestPassword123!',
            role=User.Role.TUTOR,
            first_name='Rahul',
            last_name='Verma'
        )
        self.tutor = TutorProfile.objects.create(
            user=self.tutor_user,
            headline='Physics Faculty',
            verification_status=TutorProfile.VerificationStatus.VERIFIED
        )
        self.client.login(username='parent_user', password='TestPassword123!')

    def test_toggle_save_tutor_standard(self):
        url = reverse('tutors:toggle_save', args=[self.tutor.pk])
        response = self.client.post(url, follow=True)
        self.assertEqual(response.status_code, 200)
        self.assertTrue(SavedTutor.objects.filter(user=self.parent_user, tutor=self.tutor).exists())

        # Toggle again removes it
        response2 = self.client.post(url, follow=True)
        self.assertEqual(response2.status_code, 200)
        self.assertFalse(SavedTutor.objects.filter(user=self.parent_user, tutor=self.tutor).exists())

    def test_toggle_save_tutor_ajax(self):
        url = reverse('tutors:toggle_save', args=[self.tutor.pk])
        response = self.client.post(url, headers={'x-requested-with': 'XMLHttpRequest'})
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data['saved'])
        self.assertEqual(data['total_saved'], 1)

    def test_saved_tutors_list_view(self):
        SavedTutor.objects.create(user=self.parent_user, tutor=self.tutor)
        url = reverse('tutors:saved_tutors')
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Rahul Verma')


class TutorCompareTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.u1 = User.objects.create_user(username='tutor_a', password='pass', role=User.Role.TUTOR, first_name='TutorA')
        self.u2 = User.objects.create_user(username='tutor_b', password='pass', role=User.Role.TUTOR, first_name='TutorB')
        self.t1 = TutorProfile.objects.create(user=self.u1, headline='Maths Specialist', verification_status=TutorProfile.VerificationStatus.VERIFIED)
        self.t2 = TutorProfile.objects.create(user=self.u2, headline='Science Specialist', verification_status=TutorProfile.VerificationStatus.VERIFIED)

    def test_compare_view_with_valid_ids(self):
        url = f"{reverse('tutors:compare')}?ids={self.t1.id},{self.t2.id}"
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'TutorA')
        self.assertContains(response, 'TutorB')
        self.assertContains(response, 'Side-by-Side Tutor Comparison')

    def test_compare_view_with_empty_or_invalid_ids(self):
        url = f"{reverse('tutors:compare')}?ids=99999,abc"
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
