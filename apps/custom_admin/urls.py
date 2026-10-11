from django.urls import path
from . import views

app_name = 'custom_admin'

urlpatterns = [
    path('', views.dashboard_view, name='dashboard'),
    path('tutors/', views.tutors_list_view, name='tutors'),
    path('tutors/<int:pk>/', views.tutor_detail_view, name='tutor_detail'),
    path('parents/', views.parents_list_view, name='parents'),
    path('leads/', views.leads_list_view, name='leads'),
    path('commissions/', views.commissions_view, name='commissions'),
    path('subscriptions/', views.subscriptions_view, name='subscriptions'),
    path('financials/', views.financials_view, name='financials'),
    path('complaints/', views.complaints_view, name='complaints'),
    path('announcements/', views.announcements_view, name='announcements'),
    path('branding/', views.branding_view, name='branding'),
    path('theme/', views.theme_view, name='theme'),
    path('reports/', views.reports_view, name='reports'),
    path('audit-logs/', views.audit_logs_view, name='audit_logs'),
]
