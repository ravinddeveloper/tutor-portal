import uuid
from django.db import models
from django.conf import settings
from django.utils.translation import gettext_lazy as _
from apps.tutors.models import TutorProfile
from apps.parents.models import ParentProfile, StudentProfile
from apps.leads.models import TuitionRequirement

class DemoClass(models.Model):
    class Status(models.TextChoices):
        REQUESTED = 'REQUESTED', _('Requested')
        PROPOSED = 'PROPOSED', _('Time Proposed by Tutor')
        CONFIRMED = 'CONFIRMED', _('Confirmed by Parent')
        COMPLETED = 'COMPLETED', _('Completed')
        CANCELLED = 'CANCELLED', _('Cancelled')
        RESCHEDULED = 'RESCHEDULED', _('Rescheduled')
        NO_SHOW = 'NO_SHOW', _('No Show')

    class Mode(models.TextChoices):
        HOME = 'HOME', _('In-Person at Student Home')
        ONLINE = 'ONLINE', _('Live Online Demo')

    requirement = models.ForeignKey(TuitionRequirement, on_delete=models.CASCADE, related_name='demo_classes')
    tutor = models.ForeignKey(TutorProfile, on_delete=models.CASCADE, related_name='demo_classes')
    parent = models.ForeignKey(ParentProfile, on_delete=models.CASCADE, related_name='demo_classes')
    
    mode = models.CharField(max_length=20, choices=Mode.choices, default=Mode.ONLINE)
    scheduled_datetime = models.DateTimeField()
    duration_minutes = models.PositiveIntegerField(default=45)
    meeting_link = models.URLField(max_length=500, blank=True, help_text=_('Online meeting link if mode is online'))
    address = models.TextField(blank=True, help_text=_('Location address if home demo'))
    
    status = models.CharField(max_length=25, choices=Status.choices, default=Status.REQUESTED)
    tutor_notes = models.TextField(blank=True)
    parent_feedback = models.TextField(blank=True)
    is_parent_satisfied = models.BooleanField(null=True, blank=True)
    attendance_confirmed_by_parent = models.BooleanField(default=False)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-scheduled_datetime']

    def __str__(self):
        return f"Demo: {self.tutor.display_name} with {self.parent.display_name} ({self.get_status_display()})"


class TuitionEngagement(models.Model):
    class Status(models.TextChoices):
        ACTIVE = 'ACTIVE', _('Active & Ongoing')
        COMPLETED = 'COMPLETED', _('Successfully Completed')
        TERMINATED = 'TERMINATED', _('Discontinued / Cancelled')
        ON_HOLD = 'ON_HOLD', _('Temporarily On Hold')
        DISPUTED = 'DISPUTED', _('Under Dispute')

    class BillingCycle(models.TextChoices):
        MONTHLY = 'MONTHLY', _('Monthly')
        PER_CLASS = 'PER_CLASS', _('Per Session / Class')
        HOURLY = 'HOURLY', _('Hourly')

    engagement_id = models.CharField(max_length=30, unique=True, db_index=True)
    requirement = models.ForeignKey(TuitionRequirement, on_delete=models.CASCADE, related_name='engagements')
    tutor = models.ForeignKey(TutorProfile, on_delete=models.CASCADE, related_name='engagements')
    parent = models.ForeignKey(ParentProfile, on_delete=models.CASCADE, related_name='engagements')
    student = models.ForeignKey(StudentProfile, on_delete=models.SET_NULL, null=True, blank=True, related_name='engagements')
    
    agreed_subjects = models.CharField(max_length=255)
    agreed_fee = models.DecimalField(max_digits=10, decimal_places=2, help_text=_('Agreed tuition fee amount'))
    billing_cycle = models.CharField(max_length=20, choices=BillingCycle.choices, default=BillingCycle.MONTHLY)
    
    schedule_summary = models.CharField(max_length=255, default='Mon, Wed, Fri (5:00 PM - 6:30 PM)')
    start_date = models.DateField()
    end_date = models.DateField(null=True, blank=True)
    
    status = models.CharField(max_length=25, choices=Status.choices, default=Status.ACTIVE, db_index=True)
    total_classes_conducted = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def save(self, *args, **kwargs):
        if not self.engagement_id:
            self.engagement_id = f"ENG-{uuid.uuid4().hex[:7].upper()}"
        super().save(*args, **kwargs)

    def __str__(self):
        return f"[{self.engagement_id}] {self.tutor.display_name} -> {self.parent.display_name} ({self.get_status_display()})"


class LessonSchedule(models.Model):
    class Status(models.TextChoices):
        SCHEDULED = 'SCHEDULED', _('Scheduled')
        COMPLETED = 'COMPLETED', _('Completed')
        RESCHEDULED = 'RESCHEDULED', _('Rescheduled')
        CANCELLED = 'CANCELLED', _('Cancelled')

    engagement = models.ForeignKey(TuitionEngagement, on_delete=models.CASCADE, related_name='lessons')
    title = models.CharField(max_length=200, default='Regular Tuition Session')
    scheduled_datetime = models.DateTimeField()
    duration_minutes = models.PositiveIntegerField(default=60)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.SCHEDULED)
    meeting_link = models.URLField(max_length=500, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['scheduled_datetime']

    def __str__(self):
        return f"{self.engagement.engagement_id} Lesson: {self.title} at {self.scheduled_datetime.strftime('%Y-%m-%d %H:%M')}"


class LessonRecord(models.Model):
    class Attendance(models.TextChoices):
        PRESENT = 'PRESENT', _('Present')
        ABSENT = 'ABSENT', _('Absent')
        LATE = 'LATE', _('Joined Late')

    lesson = models.OneToOneField(LessonSchedule, on_delete=models.CASCADE, related_name='record')
    attendance = models.CharField(max_length=20, choices=Attendance.choices, default=Attendance.PRESENT)
    topics_covered = models.TextField(help_text=_('Concepts and exercises taught during this session'))
    homework_assigned = models.TextField(blank=True)
    tutor_remarks = models.TextField(blank=True)
    parent_acknowledged = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Record for {self.lesson.title} ({self.attendance})"


class StudentProgressReport(models.Model):
    engagement = models.ForeignKey(TuitionEngagement, on_delete=models.CASCADE, related_name='progress_reports')
    report_title = models.CharField(max_length=200, default='Monthly Academic Progress Review')
    report_period = models.CharField(max_length=100, default='October 2026')
    topics_completed = models.TextField()
    student_strengths = models.TextField()
    areas_for_improvement = models.TextField()
    test_score_or_grade = models.CharField(max_length=50, blank=True, help_text=_('e.g. 92% in Unit Test, A Grade'))
    recommendations = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Progress Report: {self.report_period} - {self.engagement.engagement_id}"


class Review(models.Model):
    tutor = models.ForeignKey(TutorProfile, on_delete=models.CASCADE, related_name='reviews')
    parent = models.ForeignKey(ParentProfile, on_delete=models.CASCADE, related_name='reviews_given')
    engagement = models.ForeignKey(TuitionEngagement, on_delete=models.SET_NULL, null=True, blank=True, related_name='reviews')
    
    rating = models.PositiveIntegerField(default=5, help_text=_('Star rating from 1 to 5'))
    title = models.CharField(max_length=200, help_text=_('Summary headline of review'))
    comment = models.TextField()
    is_verified_booking = models.BooleanField(default=True)
    is_approved = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.rating}★ by {self.parent.display_name} for {self.tutor.display_name}"


class Complaint(models.Model):
    class Category(models.TextChoices):
        INVALID_CONTACT = 'INVALID_CONTACT', _('Fake / Invalid Phone Number')
        TUTOR_NO_SHOW = 'TUTOR_NO_SHOW', _('Tutor Did Not Attend Demo/Class')
        PARENT_NO_RESPONSE = 'PARENT_NO_RESPONSE', _('Parent Not Responding')
        PAYMENT_DISPUTE = 'PAYMENT_DISPUTE', _('Fee / Payment Dispute')
        UNPROFESSIONAL = 'UNPROFESSIONAL', _('Unprofessional Behavior')
        OTHER = 'OTHER', _('Other Issue')

    class Status(models.TextChoices):
        OPEN = 'OPEN', _('Open')
        INVESTIGATING = 'INVESTIGATING', _('Under Investigation')
        RESOLVED = 'RESOLVED', _('Resolved')
        DISMISSED = 'DISMISSED', _('Dismissed')

    complaint_id = models.CharField(max_length=30, unique=True)
    filed_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='complaints_filed')
    against_user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name='complaints_received')
    requirement = models.ForeignKey(TuitionRequirement, on_delete=models.SET_NULL, null=True, blank=True, related_name='complaints')
    
    category = models.CharField(max_length=30, choices=Category.choices, default=Category.INVALID_CONTACT)
    subject = models.CharField(max_length=255)
    description = models.TextField()
    evidence_url = models.URLField(max_length=500, blank=True)
    
    status = models.CharField(max_length=25, choices=Status.choices, default=Status.OPEN)
    resolution_notes = models.TextField(blank=True)
    credits_refunded = models.PositiveIntegerField(default=0)
    resolved_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name='resolved_complaints')
    resolved_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def save(self, *args, **kwargs):
        if not self.complaint_id:
            self.complaint_id = f"CMP-{uuid.uuid4().hex[:7].upper()}"
        super().save(*args, **kwargs)

    def __str__(self):
        return f"[{self.complaint_id}] {self.subject} ({self.get_status_display()})"
