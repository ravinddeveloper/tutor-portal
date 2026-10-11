from django.db import models
from django.conf import settings
from django.utils.translation import gettext_lazy as _
from apps.leads.models import TuitionRequirement

class Conversation(models.Model):
    user_a = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='conversations_as_a')
    user_b = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='conversations_as_b')
    requirement = models.ForeignKey(TuitionRequirement, on_delete=models.SET_NULL, null=True, blank=True, related_name='conversations')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-updated_at']

    def get_other_participant(self, user):
        return self.user_b if self.user_a == user else self.user_a

    def __str__(self):
        return f"Chat: {self.user_a.display_name} & {self.user_b.display_name}"


class Message(models.Model):
    conversation = models.ForeignKey(Conversation, on_delete=models.CASCADE, related_name='messages')
    sender = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='sent_messages')
    body = models.TextField()
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['created_at']

    def __str__(self):
        return f"{self.sender.display_name}: {self.body[:40]}"


class Notification(models.Model):
    class Type(models.TextChoices):
        LEAD_ALERT = 'LEAD_ALERT', _('Matching Tuition Lead Alert')
        APPLICATION_ALERT = 'APPLICATION_ALERT', _('New Tutor Application')
        DEMO_ALERT = 'DEMO_ALERT', _('Demo Class Update')
        CONFIRMATION_ALERT = 'CONFIRMATION_ALERT', _('Tuition Confirmed')
        WALLET_ALERT = 'WALLET_ALERT', _('Wallet / Credit Alert')
        COMMISSION_ALERT = 'COMMISSION_ALERT', _('Commission Notice')
        SYSTEM_ALERT = 'SYSTEM_ALERT', _('System Announcement')

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='notifications')
    title = models.CharField(max_length=200)
    message = models.TextField()
    notification_type = models.CharField(max_length=30, choices=Type.choices, default=Type.SYSTEM_ALERT)
    action_url = models.CharField(max_length=300, blank=True)
    is_read = models.BooleanField(default=False, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"[{self.user.display_name}] {self.title}"
