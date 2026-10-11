from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
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
