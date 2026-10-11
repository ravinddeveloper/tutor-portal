from django.urls import path
from . import views

app_name = 'accounts'

urlpatterns = [
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
    path('register/parent/', views.register_parent_view, name='register_parent'),
    path('register/tutor/', views.register_tutor_view, name='register_tutor'),
    path('dashboard-redirect/', views.dashboard_redirect_view, name='dashboard_redirect'),
]
