from django.urls import path
from .import views

app_name='booking'

urlpatterns = [
    path('new', views.BookView.as_view(), name='book'),
    path('cancel/<int:booking_id>', views.CancelBooking.as_view(), name='cancel_booking'),
    path('my_bookings', views.MyBookings.as_view(), name='my_bookings'),
]