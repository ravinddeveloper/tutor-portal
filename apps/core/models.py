from django.db import models
from django.conf import settings
from django.utils.translation import gettext_lazy as _

class CompanySettings(models.Model):
    """Singleton model for platform company branding, contact details, currency, and business defaults."""
    company_name = models.CharField(max_length=150, default='EduTutor Pro')
    tagline = models.CharField(max_length=255, default='Premier Home & Online Tuition Marketplace')
    logo_url = models.URLField(max_length=500, blank=True, default='')
    favicon_url = models.URLField(max_length=500, blank=True, default='')
    support_email = models.EmailField(default='support@edututorpro.com')
    support_phone = models.CharField(max_length=30, default='+91 98765 43210')
    whatsapp_number = models.CharField(max_length=30, default='+91 98765 43210')
    office_address = models.TextField(default='Level 4, Innovate Tower, Indiranagar 100ft Road, Bengaluru, Karnataka 560038')
    
    currency_symbol = models.CharField(max_length=10, default='₹')
    currency_code = models.CharField(max_length=10, default='INR')
    tax_percentage = models.DecimalField(max_digits=5, decimal_places=2, default=18.00)
    tax_name = models.CharField(max_length=30, default='GST')
    
    invoice_prefix = models.CharField(max_length=20, default='INV-')
    receipt_prefix = models.CharField(max_length=20, default='REC-')
    lead_id_prefix = models.CharField(max_length=20, default='TUT-')
    
    # Global Revenue / Commission Feature Switch
    commission_enabled = models.BooleanField(
        default=True,
        help_text=_('Global toggle to enable or disable commission calculations platform-wide')
    )
    referrals_enabled = models.BooleanField(default=True)
    referral_reward_credits = models.IntegerField(default=5, help_text=_('Bonus contact credits for referring user'))

    # Legal / Disclosures
    terms_and_conditions = models.TextField(
        default="All tuition agreements arranged between tutors and clients are subject to standard professional conduct guidelines."
    )
    privacy_policy = models.TextField(
        default="We respect the confidentiality of student records and tutor personal credentials."
    )
    refund_policy = models.TextField(
        default="Credits spent on invalid contacts (e.g. wrong phone number) may be replaced upon verification within 7 days."
    )
    commission_policy = models.TextField(
        default="Where enabled, commission on confirmed tuition engagements is settled in accordance with effective rules."
    )
    
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = _('Company Settings')
        verbose_name_plural = _('Company Settings')

    def save(self, *args, **kwargs):
        self.pk = 1
        super().save(*args, **kwargs)

    @classmethod
    def get_settings(cls):
        obj, created = cls.objects.get_or_create(pk=1)
        return obj

    def __str__(self):
        return f"{self.company_name} Configuration"


class ThemeSettings(models.Model):
    """Singleton model for dynamic theme colors, styling tokens, and mode customization."""
    theme_preset = models.CharField(max_length=50, default='Modern Indigo')
    primary_color = models.CharField(max_length=20, default='#4f46e5')       # Indigo
    secondary_color = models.CharField(max_length=20, default='#06b6d4')     # Cyan
    accent_color = models.CharField(max_length=20, default='#f59e0b')        # Amber
    background_color = models.CharField(max_length=20, default='#f8fafc')    # Slate-50
    surface_color = models.CharField(max_length=20, default='#ffffff')       # White
    text_color = models.CharField(max_length=20, default='#0f172a')          # Slate-900
    sidebar_color = models.CharField(max_length=20, default='#1e293b')       # Slate-800
    border_radius = models.CharField(max_length=20, default='0.75rem')
    dark_mode_enabled = models.BooleanField(default=False)

    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = _('Theme Settings')
        verbose_name_plural = _('Theme Settings')

    def save(self, *args, **kwargs):
        self.pk = 1
        super().save(*args, **kwargs)

    @classmethod
    def get_settings(cls):
        obj, created = cls.objects.get_or_create(pk=1)
        return obj

    def __str__(self):
        return f"Theme: {self.theme_preset}"


class Announcement(models.Model):
    class TargetRole(models.TextChoices):
        ALL = 'ALL', _('All Users')
        TUTOR = 'TUTOR', _('Tutors Only')
        PARENT = 'PARENT', _('Parents Only')
        STUDENT = 'STUDENT', _('Students Only')

    class Priority(models.TextChoices):
        LOW = 'LOW', _('Low')
        MEDIUM = 'MEDIUM', _('Normal')
        HIGH = 'HIGH', _('High')
        URGENT = 'URGENT', _('Urgent')

    title = models.CharField(max_length=255)
    content = models.TextField()
    badge_text = models.CharField(max_length=50, blank=True, default='Notice')
    target_role = models.CharField(max_length=20, choices=TargetRole.choices, default=TargetRole.ALL)
    priority = models.CharField(max_length=20, choices=Priority.choices, default=Priority.MEDIUM)
    target_city = models.CharField(max_length=100, blank=True, help_text=_('Leave blank for all cities'))
    is_published = models.BooleanField(default=True)
    is_featured = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return self.title


class AuditLog(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name='audit_actions')
    action = models.CharField(max_length=100)
    resource_type = models.CharField(max_length=100)
    resource_id = models.CharField(max_length=100, blank=True)
    details = models.TextField(blank=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"[{self.created_at.strftime('%Y-%m-%d %H:%M')}] {self.user} - {self.action} on {self.resource_type}:{self.resource_id}"
