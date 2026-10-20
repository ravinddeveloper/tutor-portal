from django.db import models
from django.conf import settings
from django.utils.translation import gettext_lazy as _

class TutorProfile(models.Model):
    class TeachingMode(models.TextChoices):
        HOME_ONLY = 'HOME_ONLY', _('Home Tuition Only')
        ONLINE_ONLY = 'ONLINE_ONLY', _('Online Tuition Only')
        BOTH_HOME_ONLINE = 'BOTH_HOME_ONLINE', _('Both Home & Online Tuition')

    class Gender(models.TextChoices):
        MALE = 'MALE', _('Male')
        FEMALE = 'FEMALE', _('Female')
        OTHER = 'OTHER', _('Other / Prefer not to say')

    class VerificationStatus(models.TextChoices):
        DRAFT = 'DRAFT', _('Draft')
        SUBMITTED = 'SUBMITTED', _('Submitted for Review')
        UNDER_REVIEW = 'UNDER_REVIEW', _('Under Review')
        VERIFIED = 'VERIFIED', _('Verified Profile')
        REJECTED = 'REJECTED', _('Rejected')
        SUSPENDED = 'SUSPENDED', _('Suspended')

    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='tutor_profile')
    headline = models.CharField(max_length=200, blank=True, help_text=_('e.g. Senior CBSE & ICSE Mathematics Faculty with 7+ Yrs Exp'))
    bio = models.TextField(blank=True, help_text=_('Detailed teaching philosophy, methodology, and student success highlights'))
    gender = models.CharField(max_length=15, choices=Gender.choices, default=Gender.MALE)
    date_of_birth = models.DateField(null=True, blank=True)
    experience_years = models.PositiveIntegerField(default=2)
    highest_qualification = models.CharField(max_length=150, default='Bachelor of Science')
    institution_name = models.CharField(max_length=200, blank=True)
    
    teaching_mode = models.CharField(max_length=25, choices=TeachingMode.choices, default=TeachingMode.BOTH_HOME_ONLINE)
    hourly_rate = models.DecimalField(max_digits=10, decimal_places=2, default=500.00)
    monthly_rate_estimate = models.DecimalField(max_digits=10, decimal_places=2, default=5000.00)

    # Location
    primary_city = models.CharField(max_length=100, default='Bengaluru', db_index=True)
    primary_locality = models.CharField(max_length=150, default='Indiranagar', db_index=True)
    service_radius_km = models.PositiveIntegerField(default=10, help_text=_('Service radius for home tuition in kilometers'))
    private_address = models.TextField(blank=True, help_text=_('Confidential residential address for verification only'))

    languages_spoken = models.CharField(max_length=255, default='English, Hindi')
    online_tools = models.CharField(max_length=255, blank=True, default='Zoom, Google Meet, Digital Pen Tablet')
    demo_video_url = models.URLField(max_length=500, blank=True, help_text=_('Demo introduction video link (YouTube, Vimeo, Drive)'))
    average_response_time_minutes = models.PositiveIntegerField(default=12, help_text=_('Average lead response speed in minutes'))

    # Verification & Quality
    verification_status = models.CharField(max_length=25, choices=VerificationStatus.choices, default=VerificationStatus.SUBMITTED, db_index=True)
    verification_notes = models.TextField(blank=True, help_text=_('Internal administrator/operations notes'))
    verified_at = models.DateTimeField(null=True, blank=True)
    verified_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name='verified_tutors')
    
    is_featured = models.BooleanField(default=False, db_index=True)
    profile_score = models.PositiveIntegerField(default=85, help_text=_('Calculated profile completeness & trust score 0-100'))
    average_rating = models.DecimalField(max_digits=3, decimal_places=2, default=4.90)
    total_reviews = models.PositiveIntegerField(default=0)
    total_completed_tuitions = models.PositiveIntegerField(default=0)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-is_featured', '-average_rating', '-created_at']

    @property
    def is_verified(self):
        return self.verification_status == self.VerificationStatus.VERIFIED

    @property
    def display_name(self):
        return self.user.display_name

    @property
    def is_fast_responder(self):
        return self.average_response_time_minutes <= 15

    @property
    def is_top_ranked(self):
        return self.average_rating >= 4.80 or self.is_featured or self.total_completed_tuitions >= 3

    @property
    def ranking_badge(self):
        if self.average_rating >= 4.90 and self.total_completed_tuitions >= 5:
            return "Top 1% Faculty"
        elif self.average_rating >= 4.80 or self.is_featured:
            return "Top 5% Educator"
        return "Verified Educator"

    def calculate_completeness(self):
        """
        Dynamically calculates profile completeness percentage and actionable checklist.
        Returns a dict: {'score': int, 'checklist': list, 'is_complete': bool, 'remaining_count': int}
        """
        checklist = []
        score = 0

        # 1. Basic Bio & Headline (20 pts)
        has_basic = bool(self.headline and self.bio and len(self.bio.strip()) >= 30)
        checklist.append({
            'label': 'Professional Headline & Teaching Philosophy',
            'points': 20,
            'completed': has_basic,
            'url_name': 'tutors:profile_edit',
            'action_label': 'Edit Bio'
        })
        if has_basic:
            score += 20

        # 2. Teaching Subjects & Fee (20 pts)
        sub_count = self.subjects.count()
        has_subjects = sub_count > 0
        checklist.append({
            'label': f'Teaching Subjects & Fee ({sub_count} added)',
            'points': 20,
            'completed': has_subjects,
            'url_name': 'tutors:subjects_manage',
            'action_label': 'Manage Subjects'
        })
        if has_subjects:
            score += 20

        # 3. Academic Qualifications (20 pts)
        qual_count = self.qualifications.count()
        has_qual = qual_count > 0
        checklist.append({
            'label': f'Academic Degrees & Diplomas ({qual_count} added)',
            'points': 20,
            'completed': has_qual,
            'url_name': 'tutors:profile_edit',
            'action_label': 'Add Degrees'
        })
        if has_qual:
            score += 20

        # 4. Identity & Credential Documents (20 pts)
        doc_count = self.documents.count()
        has_docs = doc_count > 0
        checklist.append({
            'label': f'Government ID & Certificates ({doc_count} uploaded)',
            'points': 20,
            'completed': has_docs,
            'url_name': 'tutors:documents_upload',
            'action_label': 'Upload Documents'
        })
        if has_docs:
            score += 20

        # 5. Demo / Teaching Introduction Video (+20 pts Boost)
        has_video = bool(self.demo_video_url and len(self.demo_video_url.strip()) >= 6)
        checklist.append({
            'label': 'Demo Video / Teaching Introduction (+20% Search Boost)',
            'points': 20,
            'completed': has_video,
            'url_name': 'tutors:profile_edit',
            'action_label': 'Add Demo Video'
        })
        if has_video:
            score += 20

        return {
            'score': score,
            'checklist': checklist,
            'is_complete': score == 100,
            'has_video': has_video,
            'remaining_count': sum(1 for item in checklist if not item['completed']),
            'strength_label': '100% Elite' if score == 100 else ('80% Advanced' if score >= 80 else f'{score}% In Progress')
        }

    def __str__(self):
        return f"{self.display_name} - {self.primary_city} ({self.get_verification_status_display()})"


class TutorQualification(models.Model):
    tutor = models.ForeignKey(TutorProfile, on_delete=models.CASCADE, related_name='qualifications')
    degree_name = models.CharField(max_length=150)
    field_of_study = models.CharField(max_length=150)
    institution = models.CharField(max_length=200)
    year_of_passing = models.PositiveIntegerField(default=2020)
    grade_or_percentage = models.CharField(max_length=50, blank=True)

    def __str__(self):
        return f"{self.degree_name} in {self.field_of_study} - {self.institution}"


class TutorDocument(models.Model):
    class DocumentType(models.TextChoices):
        GOVT_ID = 'GOVT_ID', _('Government Photo ID (Aadhaar/Passport/Driving License)')
        DEGREE_CERTIFICATE = 'DEGREE', _('Degree / Graduation Certificate')
        EXPERIENCE_CERTIFICATE = 'EXPERIENCE', _('Experience Letter / Teacher ID')
        BACKGROUND_CHECK = 'BACKGROUND', _('Background Verification / Police Clearance')

    class Status(models.TextChoices):
        PENDING = 'PENDING', _('Pending Review')
        VERIFIED = 'VERIFIED', _('Verified')
        REJECTED = 'REJECTED', _('Rejected')

    tutor = models.ForeignKey(TutorProfile, on_delete=models.CASCADE, related_name='documents')
    document_type = models.CharField(max_length=30, choices=DocumentType.choices, default=DocumentType.GOVT_ID)
    document_name = models.CharField(max_length=200, blank=True)
    document_file = models.FileField(upload_to='tutor_docs/', blank=True, null=True)
    document_url = models.URLField(max_length=500, blank=True, help_text=_('Simulated or external document preview link'))
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDING)
    rejection_reason = models.TextField(blank=True)
    uploaded_at = models.DateTimeField(auto_now_add=True)
    verified_at = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return f"{self.get_document_type_display()} for {self.tutor.display_name} ({self.get_status_display()})"


class TutorSubject(models.Model):
    tutor = models.ForeignKey(TutorProfile, on_delete=models.CASCADE, related_name='subjects')
    subject_name = models.CharField(max_length=100, db_index=True)
    classes_offered = models.CharField(max_length=150, help_text=_('e.g. Class 9-10, Class 11-12, Foundation'))
    curriculum = models.CharField(max_length=150, default='CBSE, ICSE, State Board')
    fee_per_month = models.DecimalField(max_digits=10, decimal_places=2, default=5000.00)

    class Meta:
        unique_together = ('tutor', 'subject_name')

    def __str__(self):
        return f"{self.subject_name} ({self.classes_offered}) - {self.tutor.display_name}"


class TutorAvailability(models.Model):
    class DayOfWeek(models.IntegerChoices):
        MONDAY = 0, _('Monday')
        TUESDAY = 1, _('Tuesday')
        WEDNESDAY = 2, _('Wednesday')
        THURSDAY = 3, _('Thursday')
        FRIDAY = 4, _('Friday')
        SATURDAY = 5, _('Saturday')
        SUNDAY = 6, _('Sunday')

    class Slot(models.TextChoices):
        MORNING = 'MORNING', _('Morning (7 AM - 12 PM)')
        AFTERNOON = 'AFTERNOON', _('Afternoon (12 PM - 4 PM)')
        EVENING = 'EVENING', _('Evening (4 PM - 8 PM)')
        NIGHT = 'NIGHT', _('Night (8 PM - 10 PM)')

    tutor = models.ForeignKey(TutorProfile, on_delete=models.CASCADE, related_name='availabilities')
    day_of_week = models.IntegerField(choices=DayOfWeek.choices, default=DayOfWeek.MONDAY)
    slot = models.CharField(max_length=20, choices=Slot.choices, default=Slot.EVENING)
    is_active = models.BooleanField(default=True)

    class Meta:
        unique_together = ('tutor', 'day_of_week', 'slot')

    def __str__(self):
        return f"{self.tutor.display_name} - {self.get_day_of_week_display()} ({self.get_slot_display()})"


class SavedTutor(models.Model):
    """Bookmarks / shortlists saved by students and parents."""
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='saved_tutors')
    tutor = models.ForeignKey(TutorProfile, on_delete=models.CASCADE, related_name='saved_by_users')
    notes = models.CharField(max_length=255, blank=True, help_text=_('Personal notes on why this tutor was saved'))
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('user', 'tutor')
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.user.display_name} saved {self.tutor.display_name}"


class TutorPipelineCard(models.Model):
    """
    Kanban-style visual lead conversion pipeline for educators.
    Tracks each tuition opportunity across 5 operational stages:
    - APPLIED (Unlocked / applied)
    - DEMO_SCHEDULED (Trial demo confirmed / proposed)
    - DEMO_COMPLETED (Trial class delivered)
    - WON (Active regular tuition confirmed)
    - LOST (Parent chose another tutor / cancelled)
    """
    class Stage(models.TextChoices):
        APPLIED = 'APPLIED', _('Applied / Unlocked')
        DEMO_SCHEDULED = 'DEMO_SCHEDULED', _('Demo Scheduled')
        DEMO_COMPLETED = 'DEMO_COMPLETED', _('Demo Completed')
        WON = 'WON', _('Won (Tuition Active)')
        LOST = 'LOST', _('Lost / Inactive')

    tutor = models.ForeignKey(TutorProfile, on_delete=models.CASCADE, related_name='pipeline_cards')
    requirement = models.ForeignKey('leads.TuitionRequirement', on_delete=models.CASCADE, related_name='tutor_pipeline_cards')
    stage = models.CharField(max_length=25, choices=Stage.choices, default=Stage.APPLIED, db_index=True)
    notes = models.TextField(blank=True, help_text=_('Personal notes, parent preferences, or next steps'))
    estimated_monthly_value = models.DecimalField(max_digits=10, decimal_places=2, default=5000.00)
    updated_at = models.DateTimeField(auto_now=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('tutor', 'requirement')
        ordering = ['-updated_at']

    def __str__(self):
        return f"{self.tutor.display_name} - {self.requirement.lead_id} [{self.get_stage_display()}]"


