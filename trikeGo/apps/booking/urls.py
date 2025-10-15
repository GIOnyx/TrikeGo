# booking/urls.py
from django.urls import path
from . import views

app_name = 'booking'
urlpatterns = [
    path('create/', views.create_booking, name='create_booking'),
    path('<int:booking_id>/', views.booking_detail, name='booking_detail'),
    path('<int:booking_id>/cancel/', views.cancel_booking, name='cancel_booking'),
    # Add other driver actions here (e.g., /start/, /complete/)
    
]