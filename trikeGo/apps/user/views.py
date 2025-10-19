# In trikeGo/user/views.py

from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login
from django.contrib import messages
from django.views import View
from django.views.decorators.http import require_POST
from django.shortcuts import get_object_or_404
from django.utils import timezone
from .forms import DriverRegistrationForm, RiderRegistrationForm, LoginForm, DriverVerificationForm
from .models import Driver, Rider, CustomUser
from apps.booking.forms import BookingForm
from datetime import date
from apps.booking.models import Booking
import json
from django.http import JsonResponse
from django.contrib.auth.decorators import login_required
from django.views.decorators.csrf import csrf_exempt
from apps.booking.services import RoutingService
from apps.booking.models import DriverLocation
from datetime import timedelta


class LandingPage(View):
    template_name = 'user/landingPage.html'
    def get(self, request):
        form = LoginForm()
        return render(request, self.template_name, {'form': form})

class Login(View):
    template_name = 'user/landingPage.html'

    def post(self, request):
        form = LoginForm(request, data=request.POST)
        if form.is_valid():
            username = form.cleaned_data.get('username')
            password = form.cleaned_data.get('password')
            user = authenticate(username=username, password=password)
            if user is not None:
                login(request, user)
                if user.trikego_user == 'D':
                    return redirect('user:driver_dashboard')
                elif user.trikego_user == 'R':
                    return redirect('user:rider_dashboard')
                elif user.trikego_user == 'A':
                    return redirect('user:admin_dashboard')
                return redirect('user:logged_in')

        messages.error(request, "Invalid username or password.")
        return redirect('/#login')

    def get(self, request):
        return redirect('user:landing')

class RegisterPage(View):
    template_name = 'user/register.html'

    def get(self, request):
        user_type = request.GET.get('type', 'rider')
        form = DriverRegistrationForm() if user_type == 'driver' else RiderRegistrationForm()
        return render(request, self.template_name, {'form': form, 'user_type': user_type})

    def post(self, request):
        user_type = request.POST.get('user_type', 'rider')
        form = DriverRegistrationForm(request.POST) if user_type == 'driver' else RiderRegistrationForm(request.POST)

        if form.is_valid():
            user = form.save(commit=False)
            user.trikego_user = 'D' if user_type == 'driver' else 'R'
            user.save()

            if user_type == 'driver':
                Driver.objects.create(
                    user=user,
                    license_number=form.cleaned_data.get('license_number', 'PENDING'),
                    license_image_url=form.cleaned_data.get('license_image_url', ''),
                    license_expiry=date.today(),
                    date_hired=date.today(),
                    years_of_service=0
                )
            else:
                Rider.objects.create(user=user)

            messages.success(request, f"{user_type.capitalize()} registration successful! Please log in.")
            return redirect('user:landing')

        return render(request, self.template_name, {'form': form, 'user_type': user_type})


class LoggedIn(View):
    template_name = 'user/tempLoggedIn.html'
    def get(self, request):
        return render(request, self.template_name) if request.user.is_authenticated else redirect('user:landing')

class DriverDashboard(View):
    template_name = 'booking/driver_dashboard.html'
    def get(self, request):
        if not request.user.is_authenticated or request.user.trikego_user != 'D':
            return redirect('user:landing')
        profile = Driver.objects.filter(user=request.user).first()
        available_rides = Booking.objects.filter(status='pending', driver__isnull=True)

        context = {
            'user': request.user,
            'driver_profile': profile,
            'available_rides': available_rides,
        }
        return render(request, self.template_name, context)

@require_POST
def accept_ride(request, booking_id):
    if not request.user.is_authenticated or request.user.trikego_user != 'D':
        return redirect('user:landing')

    booking = get_object_or_404(Booking, id=booking_id, status='pending', driver__isnull=True)
    booking.driver = request.user
    booking.status = 'accepted'
    booking.start_time = timezone.now()
    
    # Calculate initial route
    try:
        driver_location = DriverLocation.objects.get(driver=request.user)
        routing_service = RoutingService()
        
        # Calculate route from driver to pickup
        start_coords = (float(driver_location.longitude), float(driver_location.latitude))
        pickup_coords = (float(booking.pickup_longitude), float(booking.pickup_latitude))
        
        route_info = routing_service.calculate_route(start_coords, pickup_coords)
        
        if route_info:
            # Save route snapshot
            routing_service.save_route_snapshot(booking, route_info)
            
            # Update booking estimates
            booking.estimated_distance = Decimal(str(route_info['distance']))
            booking.estimated_duration = route_info['duration'] // 60  # Convert to minutes
            booking.estimated_arrival = timezone.now() + timedelta(seconds=route_info['duration'])
    except DriverLocation.DoesNotExist:
        messages.warning(request, "Please enable location sharing to see route information.")
    except Exception as e:
        messages.warning(request, f"Could not calculate route: {str(e)}")
    
    booking.save()
    messages.success(request, f"You have accepted the ride from {booking.pickup_address} to {booking.destination_address}.")
    return redirect('user:driver_dashboard')

class DriverActiveBookings(View):
    template_name = 'booking/driver_active_books.html'

    def get(self, request):
        if not request.user.is_authenticated or request.user.trikego_user != 'D':
            return redirect('user:landing')

        active_bookings = Booking.objects.filter(
            driver=request.user,
            status__in=['accepted', 'on_the_way', 'started']
        ).order_by('-booking_time')

        return render(request, self.template_name, {'active_bookings': active_bookings})


@require_POST
def cancel_accepted_booking(request, booking_id):
    if not request.user.is_authenticated or request.user.trikego_user != 'D':
        return redirect('user:landing')

    booking = get_object_or_404(Booking, id=booking_id, driver=request.user)

    if booking.status in ['accepted', 'on_the_way', 'started']:
        booking.status = 'pending'
        booking.driver = None
        booking.start_time = None
        booking.save()

        messages.success(request, "You have cancelled your acceptance. The booking is now available again.")
    else:
        messages.error(request, "You cannot cancel this booking anymore.")

    return redirect('user:driver_active_books')


@require_POST
def complete_booking(request, booking_id):
    if not request.user.is_authenticated or request.user.trikego_user != 'D':
        return redirect('user:landing')

    booking = get_object_or_404(Booking, id=booking_id, driver=request.user)

    if booking.status in ['accepted', 'on_the_way', 'started']:
        booking.status = 'completed'
        booking.end_time = timezone.now()
        booking.save()
        messages.success(request, "Booking marked as completed!")
    else:
        messages.error(request, "Cannot complete this booking.")

    return redirect('user:driver_active_books')

class RiderDashboard(View):
    template_name = 'booking/rider_dashboard.html'

    def get_context_data(self, request, form=None):
        if not request.user.is_authenticated or request.user.trikego_user != 'R':
            return None

        profile = Rider.objects.filter(user=request.user).first()
        booking_form = form or BookingForm()
        active_bookings = Booking.objects.filter(
            rider=request.user,
            status__in=['pending', 'accepted', 'on_the_way', 'started']
        )
        ride_history = Booking.objects.filter(
            rider=request.user,
            status__in=['completed', 'cancelled_by_rider', 'cancelled_by_driver', 'no_driver_found']
        ).order_by('-booking_time')

        return {
            'user': request.user,
            'rider_profile': profile,
            'active_bookings': active_bookings,
            'ride_history': ride_history,
            'booking_form': booking_form
        }

    def get(self, request):
        context = self.get_context_data(request)
        if context is None:
            return redirect('user:landing')
        return render(request, self.template_name, context)

    def post(self, request):
        if not request.user.is_authenticated or request.user.trikego_user != 'R':
            return redirect('user:landing')
        
        form = BookingForm(request.POST)
        
        if form.is_valid():
            booking = form.save(commit=False)
            booking.rider = request.user
            booking.save()
            
            messages.success(request, 'Your booking has been created successfully!')
            return redirect('user:rider_dashboard')
        else:
            messages.error(request, 'Please correct the errors below.')
            context = self.get_context_data(request, form=form)
            return render(request, self.template_name, context)

class AdminDashboard(View):
    template_name = 'user/admin_dashboard.html'

    def get(self, request):
        if not request.user.is_authenticated or getattr(request.user, 'trikego_user', None) != 'A':
            return redirect('user:landing')

        context = {
            "drivers": Driver.objects.select_related("user").all(),
            "riders": Rider.objects.select_related("user").all(),
            "users": CustomUser.objects.all(),
            "verification_form": DriverVerificationForm(),
        }
        return render(request, self.template_name, context)

    def post(self, request):
        if not request.user.is_authenticated or getattr(request.user, 'trikego_user', None) != 'A':
            return redirect('user:landing')

        form = DriverVerificationForm(request.POST)

        if form.is_valid():
            driver_id = form.cleaned_data['driver_id']
            driver = Driver.objects.get(id=driver_id)
            driver.is_verified = not driver.is_verified
            driver.save(update_fields=["is_verified"])
            messages.success(request, f"Driver {driver.user.username}'s verification status has been updated.")
        else:
            for field, errors in form.errors.items():
                for error in errors:
                    messages.error(request, f"{field}: {error}")

        return redirect('user:admin_dashboard')

# --- REAL-TIME TRACKING VIEWS ---

@csrf_exempt
@login_required
@require_POST
def update_driver_location(request):
    if request.user.trikego_user != 'D':
        return JsonResponse({'status': 'error', 'message': 'Only drivers can update location.'}, status=403)
    
    try:
        data = json.loads(request.body)
        lat, lon = data.get('lat'), data.get('lon')
        if lat is None or lon is None:
            return JsonResponse({'status': 'error', 'message': 'Missing lat/lon.'}, status=400)
        Driver.objects.filter(user=request.user).update(current_latitude=lat, current_longitude=lon)
        return JsonResponse({'status': 'success'})
    except Exception as e:
        return JsonResponse({'status': 'error', 'message': str(e)}, status=500)

@login_required
def get_driver_location(request, booking_id):
    booking = get_object_or_404(Booking, id=booking_id)
    if request.user != booking.rider:
        return JsonResponse({'status': 'error', 'message': 'Permission denied.'}, status=403)
    if not booking.driver:
        return JsonResponse({'status': 'error', 'message': 'No driver assigned yet.'}, status=404)
    try:
        driver_profile = Driver.objects.get(user=booking.driver)
        return JsonResponse({'status': 'success', 'lat': driver_profile.current_latitude, 'lon': driver_profile.current_longitude})
    except Driver.DoesNotExist:
        return JsonResponse({'status': 'error', 'message': 'Driver profile not found.'}, status=404)

# --- NEW: VIEWS FOR RIDER LOCATION AND DRIVER MAP ---
@csrf_exempt
@login_required
@require_POST
def update_rider_location(request):
    if request.user.trikego_user != 'R':
        return JsonResponse({'status': 'error', 'message': 'Only riders can update location.'}, status=403)
    
    try:
        data = json.loads(request.body)
        lat, lon = data.get('lat'), data.get('lon')
        if lat is None or lon is None:
            return JsonResponse({'status': 'error', 'message': 'Missing lat/lon.'}, status=400)
        Rider.objects.filter(user=request.user).update(current_latitude=lat, current_longitude=lon)
        return JsonResponse({'status': 'success'})
    except Exception as e:
        return JsonResponse({'status': 'error', 'message': str(e)}, status=500)

@login_required
def get_route_info(request, booking_id):
    booking = get_object_or_404(Booking, id=booking_id)
    # --- FIXED: Changed permission check to allow any driver to review ---
    if not request.user.is_authenticated or request.user.trikego_user != 'D':
        return JsonResponse({'status': 'error', 'message': 'Only drivers can view route info.'}, status=403)
    
    try:
        driver_profile = Driver.objects.get(user=request.user) # Use request.user to get current driver
        rider_profile = Rider.objects.get(user=booking.rider)
        
        return JsonResponse({
            'status': 'success',
            'driver_lat': driver_profile.current_latitude,
            'driver_lon': driver_profile.current_longitude,
            'rider_lat': rider_profile.current_latitude,
            'rider_lon': rider_profile.current_longitude,
            'pickup_lat': booking.pickup_latitude,
            'pickup_lon': booking.pickup_longitude,
            'destination_lat': booking.destination_latitude,
            'destination_lon': booking.destination_longitude,
        })
    except (Driver.DoesNotExist, Rider.DoesNotExist):
        return JsonResponse({'status': 'error', 'message': 'Profile not found for driver or rider.'}, status=404)

