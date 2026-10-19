from django.urls import path
from . import views

app_name = 'tutors'

urlpatterns = [
    # Public & Discovery views
    path('', views.directory_view, name='directory'),
    path('compare/', views.tutor_compare_view, name='compare'),
    path('saved/', views.saved_tutors_view, name='saved_tutors'),
    path('save/<int:pk>/', views.toggle_save_tutor_view, name='toggle_save'),
    path('<int:pk>/', views.detail_view, name='detail'),

    # Private Tutor Portal
    path('dashboard/', views.dashboard_view, name='dashboard'),
    path('profile/', views.profile_edit_view, name='profile_edit'),
    path('subjects/', views.subjects_manage_view, name='subjects_manage'),
    path('availability/', views.availability_manage_view, name='availability_manage'),
    path('documents/', views.documents_upload_view, name='documents_upload'),
    path('leads/', views.leads_browse_view, name='leads_browse'),
    path('unlocked-leads/', views.unlocked_leads_view, name='unlocked_leads'),
    path('applications/', views.applications_view, name='applications'),
    path('demos/', views.demos_view, name='demos'),
    path('engagements/', views.engagements_view, name='engagements'),
    path('billing/', views.billing_view, name='billing'),
]
