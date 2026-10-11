from .models import CompanySettings, ThemeSettings
from apps.communication.models import Notification

def global_branding_and_theme(request):
    """Context processor providing CompanySettings, ThemeSettings, and user unread notifications."""
    company = CompanySettings.get_settings()
    theme = ThemeSettings.get_settings()
    
    unread_notifications_count = 0
    if request.user.is_authenticated:
        try:
            unread_notifications_count = Notification.objects.filter(user=request.user, is_read=False).count()
        except Exception:
            unread_notifications_count = 0

    return {
        'company': company,
        'theme': theme,
        'unread_notifications_count': unread_notifications_count,
    }
