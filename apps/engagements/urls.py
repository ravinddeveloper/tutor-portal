from django.urls import path
from . import views

app_name = 'engagements'

urlpatterns = [
    path('reviews/', views.reviews_view, name='reviews'),
    path('file-complaint/', views.file_complaint_view, name='file_complaint'),
]
