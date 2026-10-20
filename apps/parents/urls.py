from django.urls import path
from . import views

app_name = 'parents'

urlpatterns = [
    path('dashboard/', views.dashboard_view, name='dashboard'),
    path('requirements/', views.requirements_list_view, name='requirements'),
    path('matches/<str:lead_id>/', views.matches_view, name='matches'),
    path('confirm/<str:lead_id>/', views.confirm_tuition_view, name='confirm_tuition'),
    path('demos/', views.demos_list_view, name='demos'),
    path('instant-demo/', views.instant_demo_booking_view, name='instant_demo_booking'),
    path('tuitions/', views.tuitions_list_view, name='tuitions'),
    path('progress-reports/<int:report_id>/', views.progress_report_detail_view, name='progress_report_detail'),
    path('students/', views.students_manage_view, name='students'),
]
