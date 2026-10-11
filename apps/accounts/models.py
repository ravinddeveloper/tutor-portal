import uuid
from django.db import models
from django.contrib.auth.models import AbstractUser
from django.utils.translation import gettext_lazy as _

class User(AbstractUser):
    class Role(models.TextChoices):
        SUPER_ADMIN = 'SUPER_ADMIN', _('Super Administrator')
        OPERATIONS = 'OPERATIONS', _('Operations Manager')
        TUTOR = 'TUTOR', _('Tutor / Educator')
        PARENT = 'PARENT', _('Parent / Guardian')
        STUDENT = 'STUDENT', _('Student')
        STAFF = 'STAFF', _('Support & Finance Staff')

    role = models.CharField(
        max_length=20,
        choices=Role.choices,
        default=Role.PARENT,
        help_text=_('User role defining default permissions and portal view')
    )
    phone_number = models.CharField(max_length=20, blank=True, db_index=True)
    is_phone_verified = models.BooleanField(default=False)
    is_email_verified = models.BooleanField(default=False)
    city = models.CharField(max_length=100, blank=True, db_index=True)
    locality = models.CharField(max_length=150, blank=True)
    avatar = models.ImageField(upload_to='avatars/', blank=True, null=True)
    avatar_url = models.URLField(max_length=500, blank=True, help_text=_('External or simulated avatar URL'))
    
    # Referral system
    referral_code = models.CharField(max_length=20, unique=True, blank=True, null=True)
    referred_by = models.ForeignKey(
        'self',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='referrals_made'
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def save(self, *args, **kwargs):
        if not self.referral_code:
            self.referral_code = f"REF{uuid.uuid4().hex[:8].upper()}"
        super().save(*args, **kwargs)

    @property
    def is_tutor(self):
        return self.role == self.Role.TUTOR

    @property
    def is_parent(self):
        return self.role == self.Role.PARENT

    @property
    def is_student(self):
        return self.role == self.Role.STUDENT

    @property
    def is_operations(self):
        return self.role in [self.Role.OPERATIONS, self.Role.SUPER_ADMIN] or self.is_superuser

    @property
    def is_super_admin(self):
        return self.role == self.Role.SUPER_ADMIN or self.is_superuser

    @property
    def display_name(self):
        name = f"{self.first_name} {self.last_name}".strip()
        return name if name else self.username

    def __str__(self):
        return f"{self.display_name} ({self.get_role_display()})"
