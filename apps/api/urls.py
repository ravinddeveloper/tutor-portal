from django.urls import path
from . import views

app_name = 'api'

urlpatterns = [
    path('tutors/', views.TutorListAPIView.as_view(), name='tutor_list'),
    path('tutors/<int:pk>/', views.TutorDetailAPIView.as_view(), name='tutor_detail'),
    path('leads/', views.PublicLeadsListAPIView.as_view(), name='leads_list'),
    path('leads/<str:lead_id>/', views.LeadDetailAPIView.as_view(), name='lead_detail'),
    path('leads/<str:lead_id>/unlock/', views.UnlockLeadAPIView.as_view(), name='lead_unlock'),
    path('leads/<str:lead_id>/matches/', views.LeadMatchesAPIView.as_view(), name='lead_matches'),
    path('subscriptions/', views.SubscriptionPlansAPIView.as_view(), name='subscriptions'),
    path('company/', views.CompanyConfigAPIView.as_view(), name='company_config'),
]
