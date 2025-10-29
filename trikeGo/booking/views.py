# In trikeGo/booking/views.py

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_POST
from django.http import JsonResponse, HttpResponseForbidden
from django.utils import timezone
from .forms import BookingForm
from .models import Booking
from user.models import CustomUser

@login_required
@require_POST # This view now only accepts POST requests from the form
def create_booking(request):
    form = BookingForm(request.POST)
    if form.is_valid():
        booking = form.save(commit=False)
        booking.rider = request.user  # Set the rider to the logged-in user
        booking.status = 'pending'    # Set the initial status
        booking.save()
        # Redirect to the new booking detail page to show status
        return redirect('booking:booking_detail', booking_id=booking.id)
    else:
        # If form is invalid, it's harder to show errors on the dashboard.
        # For now, we redirect back. A better solution would use AJAX.
        return redirect('user:rider_dashboard')

@login_required
def booking_detail(request, booking_id):
    booking = get_object_or_404(Booking, id=booking_id)

    # Security check: only the rider or driver of the booking can view it
    if request.user != booking.rider and request.user != booking.driver:
        return HttpResponseForbidden("You do not have permission to view this booking.")

    context = {
        'booking': booking
    }
    return render(request, 'booking/booking_detail.html', context)

@login_required
@require_POST
def cancel_booking(request, booking_id):
    booking = get_object_or_404(Booking, id=booking_id)

    # Security check: only the rider can cancel their own booking
    if request.user != booking.rider:
        return JsonResponse({'status': 'error', 'message': 'Permission denied.'}, status=403)

    if booking.status in ['pending', 'accepted']:
        booking.status = 'cancelled_by_rider'
        booking.end_time = timezone.now()
        booking.save()
        return JsonResponse({'status': 'success', 'message': 'Booking cancelled successfully.'})
    else:
        return JsonResponse({'status': 'error', 'message': 'This booking can no longer be cancelled.'}, status=400)
    
    
    