import uuid
from django.db import models
from django.conf import settings
from django.utils.translation import gettext_lazy as _
from apps.parents.models import ParentProfile, StudentProfile
from apps.tutors.models import TutorProfile

class TuitionRequirement(models.Model):
    class TuitionType(models.TextChoices):
        HOME_TUITION = 'HOME_TUITION', _('Home Tuition (Tutor visits student)')
        ONLINE_TUITION = 'ONLINE_TUITION', _('Online Tuition (Live Interactive)')
        TUTOR_LOCATION = 'TUTOR_LOCATION', _('At Tutor’s Location / Coaching')
        HYBRID = 'HYBRID', _('Hybrid (Mix of Home & Online)')

    class GenderPreference(models.TextChoices):
        ANY = 'ANY', _('No Preference (Any)')
        MALE = 'MALE', _('Male Tutor Preferred')
        FEMALE = 'FEMALE', _('Female Tutor Preferred')

    class BudgetType(models.TextChoices):
        MONTHLY = 'MONTHLY', _('Per Month')
        HOURLY = 'HOURLY', _('Per Hour')
        PER_CLASS = 'PER_CLASS', _('Per Class')

    class Status(models.TextChoices):
        DRAFT = 'DRAFT', _('Draft')
        PENDING_VERIFICATION = 'PENDING_VERIFICATION', _('Pending Verification')
        OPEN = 'OPEN', _('Open & Active')
        MATCHING = 'MATCHING', _('Matching In Progress')
        APPLICATIONS_RECEIVED = 'APPLICATIONS_RECEIVED', _('Applications Received')
        DEMO_SCHEDULED = 'DEMO_SCHEDULED', _('Demo Scheduled')
        TUTOR_SELECTED = 'TUTOR_SELECTED', _('Tutor Selected')
        CONFIRMED = 'CONFIRMED', _('Tuition Confirmed')
        ON_HOLD = 'ON_HOLD', _('On Hold')
        CLOSED = 'CLOSED', _('Closed')
        EXPIRED = 'EXPIRED', _('Expired')
        INVALID = 'INVALID', _('Invalid / Duplicate')

    # Unique public lead identifier
    lead_id = models.CharField(max_length=30, unique=True, db_index=True)
    parent = models.ForeignKey(ParentProfile, on_delete=models.CASCADE, related_name='requirements')
    student = models.ForeignKey(StudentProfile, on_delete=models.SET_NULL, null=True, blank=True, related_name='requirements')
    
    title = models.CharField(max_length=255, help_text=_('e.g. Home Tutor needed for Class 10 CBSE Math & Science'))
    student_class = models.CharField(max_length=100, default='Class 10')
    board_curriculum = models.CharField(max_length=100, default='CBSE')
    subjects = models.CharField(max_length=255, help_text=_('e.g. Mathematics, Physics, Chemistry'))
    tuition_type = models.CharField(max_length=30, choices=TuitionType.choices, default=TuitionType.HOME_TUITION)
    
    # Location
    city = models.CharField(max_length=100, default='Bengaluru', db_index=True)
    locality = models.CharField(max_length=150, default='Indiranagar', db_index=True)
    pincode = models.CharField(max_length=15, blank=True)
    landmark = models.CharField(max_length=200, blank=True, help_text=_('Nearby landmark or neighborhood'))

    preferred_gender = models.CharField(max_length=15, choices=GenderPreference.choices, default=GenderPreference.ANY)
    days_per_week = models.PositiveIntegerField(default=3)
    preferred_timing = models.CharField(max_length=150, default='Evening (5:00 PM - 7:00 PM)')
    session_duration_mins = models.PositiveIntegerField(default=60)
    
    budget_amount = models.DecimalField(max_digits=10, decimal_places=2, default=5000.00)
    budget_type = models.CharField(max_length=20, choices=BudgetType.choices, default=BudgetType.MONTHLY)
    target_start_date = models.DateField(null=True, blank=True)
    
    learning_goals = models.TextField(blank=True, help_text=_('Target goals, weak concepts, exam preparation notes'))
    special_instructions = models.TextField(blank=True)

    # PRIVATE CONTACT FIELDS - NEVER EXPOSED UNTIL UNLOCKED!
    parent_contact_name = models.CharField(max_length=150)
    contact_phone = models.CharField(max_length=30)
    contact_email = models.EmailField(blank=True)
    full_address = models.TextField(blank=True)

    # Lead Unlock Economics
    credits_to_unlock = models.PositiveIntegerField(default=1, help_text=_('Contact credits consumed to view contact details'))
    status = models.CharField(max_length=30, choices=Status.choices, default=Status.OPEN, db_index=True)
    assigned_staff = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name='assigned_leads')
    
    # Analytics Counters
    total_views = models.PositiveIntegerField(default=0)
    total_unlocks = models.PositiveIntegerField(default=0)
    total_applications = models.PositiveIntegerField(default=0)

    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(auto_now=True)
    expires_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['-created_at']

    def save(self, *args, **kwargs):
        if not self.lead_id:
            # Generate reference style lead id like TUT-2026-XXXX or TUT-874167
            self.lead_id = f"TUT-{uuid.uuid4().hex[:7].upper()}"
        super().save(*args, **kwargs)

    def is_unlocked_by(self, tutor_profile):
        """Checks if this requirement has been unlocked by the given tutor."""
        if not tutor_profile:
            return False
        return LeadUnlock.objects.filter(requirement=self, tutor=tutor_profile).exists()

    def __str__(self):
        return f"[{self.lead_id}] {self.title} - {self.city} ({self.get_status_display()})"


class TutorMatch(models.Model):
    requirement = models.ForeignKey(TuitionRequirement, on_delete=models.CASCADE, related_name='matched_tutors')
    tutor = models.ForeignKey(TutorProfile, on_delete=models.CASCADE, related_name='lead_matches')
    match_score = models.PositiveIntegerField(default=80, help_text=_('Compatibility score 0-100'))
    match_reasons = models.TextField(blank=True, help_text=_('Bullet points explaining why this tutor matches'))
    is_invited = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('requirement', 'tutor')
        ordering = ['-match_score', '-created_at']

    def __str__(self):
        return f"{self.tutor.display_name} matched with {self.requirement.lead_id} ({self.match_score}%)"


class LeadApplication(models.Model):
    class Status(models.TextChoices):
        PENDING = 'PENDING', _('Pending Parent Review')
        SHORTLISTED = 'SHORTLISTED', _('Shortlisted')
        DEMO_REQUESTED = 'DEMO_REQUESTED', _('Demo Requested')
        ACCEPTED = 'ACCEPTED', _('Accepted')
        REJECTED = 'REJECTED', _('Rejected')
        WITHDRAWN = 'WITHDRAWN', _('Withdrawn')

    requirement = models.ForeignKey(TuitionRequirement, on_delete=models.CASCADE, related_name='applications')
    tutor = models.ForeignKey(TutorProfile, on_delete=models.CASCADE, related_name='applications')
    cover_note = models.TextField(help_text=_('Message to the parent explaining qualifications and plan'))
    proposed_fee = models.DecimalField(max_digits=10, decimal_places=2)
    status = models.CharField(max_length=25, choices=Status.choices, default=Status.PENDING)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ('requirement', 'tutor')
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.tutor.display_name} -> {self.requirement.lead_id} ({self.get_status_display()})"


class LeadUnlock(models.Model):
    class UnlockMethod(models.TextChoices):
        CREDIT_WALLET = 'CREDIT_WALLET', _('Contact Credit Deduction')
        SUBSCRIPTION_FREE = 'SUBSCRIPTION_FREE', _('Subscription Plan Benefit')
        DIRECT_PURCHASE = 'DIRECT_PURCHASE', _('Direct Lead Purchase')
        ADMIN_OVERRIDE = 'ADMIN_OVERRIDE', _('Admin Override')

    class FeedbackStatus(models.TextChoices):
        UNCHECKED = 'UNCHECKED', _('Not Yet Verified')
        VALID_CONTACT = 'VALID_CONTACT', _('Contact Valid & In Touch')
        WRONG_PHONE = 'WRONG_PHONE', _('Wrong or Invalid Phone Number')
        ALREADY_HIRED = 'ALREADY_HIRED', _('Already Hired Another Tutor')
        NO_RESPONSE = 'NO_RESPONSE', _('No Response / Switched Off')
        REFUND_REQUESTED = 'REFUND_REQUESTED', _('Credit Refund Requested')
        REFUND_GRANTED = 'REFUND_GRANTED', _('Credit Refunded')

    requirement = models.ForeignKey(TuitionRequirement, on_delete=models.CASCADE, related_name='unlocks')
    tutor = models.ForeignKey(TutorProfile, on_delete=models.CASCADE, related_name='unlocked_leads')
    credits_spent = models.PositiveIntegerField(default=1)
    unlock_method = models.CharField(max_length=30, choices=UnlockMethod.choices, default=UnlockMethod.CREDIT_WALLET)
    unlocked_at = models.DateTimeField(auto_now_add=True)
    
    feedback_status = models.CharField(max_length=30, choices=FeedbackStatus.choices, default=FeedbackStatus.UNCHECKED)
    feedback_note = models.TextField(blank=True)

    class Meta:
        unique_together = ('requirement', 'tutor')
        ordering = ['-unlocked_at']

    def __str__(self):
        return f"{self.tutor.display_name} unlocked {self.requirement.lead_id}"
