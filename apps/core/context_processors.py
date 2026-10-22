from .models import CompanySettings, ThemeSettings
from .theme import theme_css
from apps.communication.models import Notification

import os
import time

_STATIC_VERSION_CACHE = {"value": None, "checked_at": 0.0}
_STATIC_VERSION_TTL = 60.0  # seconds


def _collect_static_version():
    """
    Build a cache-busting token from the newest static asset on disk.

    Without it browsers apply heuristic caching to stylesheets and scripts
    that carry no Cache-Control header, so users can keep running a stale
    bundle long after a deploy.  The token is appended to shared asset URLs
    in base.html, which busts the cache whenever any asset actually changes.
    """
    now = time.time()
    cached = _STATIC_VERSION_CACHE
    if cached["value"] and (now - cached["checked_at"]) < _STATIC_VERSION_TTL:
        return cached["value"]

    newest = 0.0
    roots = []

    try:
        from django.conf import settings
        from django.contrib.staticfiles import finders

        for directory in getattr(settings, "STATICFILES_DIRS", []) or []:
            roots.append(str(directory))
        for finder in finders.get_finders():
            for short_path, storage in getattr(finder, "locations", []):
                if hasattr(storage, "path"):
                    roots.append(str(storage.path))
    except Exception:
        pass

    for root in roots:
        try:
            for dirpath, _dirnames, filenames in os.walk(root):
                for filename in filenames:
                    try:
                        stamp = os.path.getmtime(os.path.join(dirpath, filename))
                    except OSError:
                        continue
                    if stamp > newest:
                        newest = stamp
        except OSError:
            continue

    token = str(int(newest)) if newest else "1"
    cached["value"] = token
    cached["checked_at"] = now
    return token


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
        'theme_css': theme_css(theme),
        'static_version': _collect_static_version(),
        'unread_notifications_count': unread_notifications_count,
    }
