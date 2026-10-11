from django.db import models
from django.conf import settings
from django.utils.translation import gettext_lazy as _

class ParentProfile(models.Model):
    class ContactPreference(models.TextChoices):
        PHONE = 'PHONE', _('Phone Call')
        WHATSAPP = 'WHATSAPP', _('WhatsApp')
        EMAIL = 'EMAIL', _('Email')
        IN_APP = 'IN_APP', _('In-App Chat Only')

    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='parent_profile')
    alternate_phone = models.CharField(max_length=20, blank=True)
    address_line = models.TextField(blank=True, help_text=_('Residential address for home tuition'))
    city = models.CharField(max_length=100, default='Bengaluru', db_index=True)
    locality = models.CharField(max_length=150, default='Indiranagar', db_index=True)
    pincode = models.CharField(max_length=10, blank=True)
    preferred_contact_method = models.CharField(
        max_length=20,
        choices=ContactPreference.choices,
        default=ContactPreference.PHONE
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    @property
    def display_name(self):
        return self.user.display_name

    def __str__(self):
        return f"{self.display_name} ({self.city}, {self.locality})"


class StudentProfile(models.Model):
    parent = models.ForeignKey(ParentProfile, on_delete=models.CASCADE, related_name='students')
    student_name = models.CharField(max_length=100)
    grade_level = models.CharField(max_length=50, help_text=_('e.g. Class 10, Class 12, Grade 8, IIT Foundation'))
    school_or_college = models.CharField(max_length=200, blank=True)
    board_curriculum = models.CharField(max_length=100, default='CBSE')
    academic_goals = models.TextField(blank=True, help_text=_('Specific objectives, e.g. Score 90%+ in Board exams, Concept clearing'))
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.student_name} - {self.grade_level} ({self.board_curriculum})"
