from django.contrib import admin
from django.urls import path, include, re_path
from django.conf import settings
from django.conf.urls.static import static
from apps.core.views import serve_dmsans_font
from django.contrib.auth import views as auth_views

urlpatterns = [
    # ── Django Built-In Secure Password Reset Flow ──
    path(
        'password-reset/',
        auth_views.PasswordResetView.as_view(
            template_name='accounts/password_reset_form.html',
            email_template_name='accounts/password_reset_email.html',
            subject_template_name='accounts/password_reset_subject.txt',
            success_url='/password-reset/done/'
        ),
        name='password_reset'
    ),
    path(
        'password-reset/done/',
        auth_views.PasswordResetDoneView.as_view(
            template_name='accounts/password_reset_done.html'
        ),
        name='password_reset_done'
    ),
    path(
        'password-reset-confirm/<uidb64>/<token>/',
        auth_views.PasswordResetConfirmView.as_view(
            template_name='accounts/password_reset_confirm.html',
            success_url='/password-reset-complete/'
        ),
        name='password_reset_confirm'
    ),
    path(
        'password-reset-complete/',
        auth_views.PasswordResetCompleteView.as_view(
            template_name='accounts/password_reset_complete.html'
        ),
        name='password_reset_complete'
    ),
    re_path(r'^(?:.*/)?DMSans-Regular\.ttf$', serve_dmsans_font, name='dmsans_font'),
    path('django-admin/', admin.site.urls), # standard django admin retained as fallback
    path('', include('apps.core.urls', namespace='core')),
    path('accounts/', include('apps.accounts.urls', namespace='accounts')),
    path('tutors/', include('apps.tutors.urls', namespace='tutors')),
    path('parents/', include('apps.parents.urls', namespace='parents')),
    path('leads/', include('apps.leads.urls', namespace='leads')),
    path('billing/', include('apps.billing.urls', namespace='billing')),
    path('engagements/', include('apps.engagements.urls', namespace='engagements')),
    path('communication/', include('apps.communication.urls', namespace='communication')),
    path('admin-portal/', include('apps.custom_admin.urls', namespace='custom_admin')),
    path('api/v1/', include('apps.api.urls', namespace='api')),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
