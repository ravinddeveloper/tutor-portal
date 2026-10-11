from django.urls import path
from . import views

app_name = 'communication'

urlpatterns = [
    path('inbox/', views.inbox_view, name='inbox'),
    path('chat/<int:conversation_id>/', views.conversation_detail_view, name='detail'),
    path('notifications/', views.notifications_list_view, name='notifications'),
]
