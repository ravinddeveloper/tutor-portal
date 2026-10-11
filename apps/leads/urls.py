from django.urls import path
from . import views

app_name = 'leads'

urlpatterns = [
    path('post/', views.post_requirement_view, name='post_requirement'),
    path('board/', views.board_view, name='board'),
    path('<str:lead_id>/', views.detail_view, name='detail'),
]
