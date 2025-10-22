# In trikeGo/user/views.py

from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login
from django.contrib import messages
from django.views import View
from django.views.decorators.http import require_POST
from django.shortcuts import get_object_or_404
from django.utils import timezone
from .forms import DriverRegistrationForm, RiderRegistrationForm, LoginForm, DriverVerificationForm, TricycleForm
from .models import Driver, Rider, CustomUser, Tricycle
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
from django.conf import settings
from decimal import Decimal


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
                # Store pending driver id in session and redirect to tricycle registration (step 2)
                pending_driver = Driver.objects.filter(user=user).first()
                if pending_driver:
                    request.session['pending_driver_id'] = pending_driver.id
                    return redirect('user:tricycle_register')
            else:
                Rider.objects.create(user=user)
            
            messages.success(request, f"{user_type.capitalize()} registration successful!")
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
        active_booking = Booking.objects.filter(
            driver=request.user,
            status__in=['accepted', 'on_the_way', 'started']
        ).order_by('-booking_time').first()

        context = {
            'user': request.user,
            'driver_profile': profile,
            'settings': settings,
            'available_rides': available_rides,
            'active_booking': active_booking,
        }
        return render(request, self.template_name, context)


class TricycleRegister(View):
    template_name = 'user/tricycle_register.html'

    def get(self, request):
        pending_id = request.session.get('pending_driver_id')
        if not pending_id:
            messages.error(request, 'No pending driver found. Please complete the first step.')
            return redirect('user:register')

        form = TricycleForm()
        return render(request, self.template_name, {'form': form, 'step': 2})

    def post(self, request):
        pending_id = request.session.get('pending_driver_id')
        if not pending_id:
            messages.error(request, 'Session expired or invalid. Please start registration again.')
            return redirect('user:register')

        form = TricycleForm(request.POST)
        if form.is_valid():
            trike = form.save(commit=False)
            try:
                driver = Driver.objects.get(id=pending_id)
            except Driver.DoesNotExist:
                messages.error(request, 'Driver profile missing. Please contact support.')
                return redirect('user:register')

            trike.driver = driver
            trike.save()

            # mark driver as not verified; approval is handled via admin verification
            driver.is_verified = False
            driver.save(update_fields=['is_verified'])

            # Notify admins via email if configured
            try:
                from django.core.mail import mail_admins
                subject = f'New tricycle registration for driver {driver.user.username}'
                message = f'Driver ID: {driver.id}\nTricycle: {trike.plate_number} ({trike.color})\nPlease review and approve.'
                mail_admins(subject, message)
            except Exception:
                # if mail not configured, still continue
                pass

            # Clear session and show confirmation
            request.session.pop('pending_driver_id', None)
            messages.success(request, 'Your application is under review.')
            return render(request, 'user/registration_complete.html')
        else:
            return render(request, self.template_name, {'form': form, 'step': 2})

@require_POST
def accept_ride(request, booking_id):
    if not request.user.is_authenticated or request.user.trikego_user != 'D':
        return redirect('user:landing')

    # Enforce: driver can only manage one active booking
    driver_has_active = Booking.objects.filter(
        driver=request.user,
        status__in=['accepted', 'on_the_way', 'started']
    ).exists()
    if driver_has_active:
        messages.error(request, "You already have an active trip. Complete or cancel it first.")
        return redirect('user:driver_dashboard')

    # Also prevent acceptance if rider already has an active trip
    booking = get_object_or_404(Booking, id=booking_id, status='pending', driver__isnull=True)
    rider_active = Booking.objects.filter(
        rider=booking.rider,
        status__in=['accepted', 'on_the_way', 'started']
    ).exists()
    if rider_active:
        messages.error(request, "Rider already has an active trip.")
        return redirect('user:driver_dashboard')

    booking.driver = request.user
    booking.status = 'accepted'
    booking.start_time = timezone.now()

    # Update statuses
    Driver.objects.filter(user=request.user).update(status='In_trip')
    Rider.objects.filter(user=booking.rider).update(status='In_trip')
    
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
            booking.estimated_duration = route_info['duration'] // 60  # minutes
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
        # Reset statuses
        Driver.objects.filter(user=request.user).update(status='Online')
        Rider.objects.filter(user=booking.rider).update(status='Available')

        messages.success(request, "You have cancelled your acceptance. The booking is now available again.")
    else:
        messages.error(request, "You cannot cancel this booking anymore.")

    return redirect('user:driver_active_books')


@require_POST
def cancel_booking(request, booking_id):
    """Allow riders to cancel their own bookings (pending or accepted)."""
    if not request.user.is_authenticated or request.user.trikego_user != 'R':
        return redirect('user:landing')

    booking = get_object_or_404(Booking, id=booking_id)
    if booking.rider != request.user:
        messages.error(request, 'Permission denied.')
        return redirect('user:rider_dashboard')

    # Only allow cancelling of pending bookings (rider cannot cancel once trip is accepted/on the way/started)
    if booking.status == 'pending':
        booking.status = 'cancelled_by_rider'
        booking.driver = None
        booking.start_time = None
        booking.save()
        messages.success(request, 'Your booking has been cancelled.')
    else:
        messages.error(request, 'This booking cannot be cancelled at this stage.')

    return redirect('user:rider_dashboard')


@require_POST
def complete_booking(request, booking_id):
    if not request.user.is_authenticated or request.user.trikego_user != 'D':
        return redirect('user:landing')

    booking = get_object_or_404(Booking, id=booking_id, driver=request.user)

    if booking.status in ['accepted', 'on_the_way', 'started']:
        booking.status = 'completed'
        booking.end_time = timezone.now()
        booking.save()
        # Reset statuses
        Driver.objects.filter(user=request.user).update(status='Online')
        Rider.objects.filter(user=booking.rider).update(status='Available')
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
            'settings': settings,
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
        
        # Restrict: rider can only have one active booking
        has_active = Booking.objects.filter(
            rider=request.user,
            status__in=['pending', 'accepted', 'on_the_way', 'started']
        ).exists()
        if has_active:
            messages.error(request, 'You already have an active ride. Please complete or cancel it first.')
            return redirect('user:rider_dashboard')
        
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
    
    # Allow: drivers to preview using their own current location; riders to view for their own booking
    if request.user.trikego_user == 'D':
        try:
            driver_profile = Driver.objects.get(user=request.user)
            rider_profile = Rider.objects.get(user=booking.rider)
        except (Driver.DoesNotExist, Rider.DoesNotExist):
            return JsonResponse({'status': 'error', 'message': 'Profile not found for driver or rider.'}, status=404)
    elif request.user.trikego_user == 'R':
        if request.user != booking.rider:
            return JsonResponse({'status': 'error', 'message': 'Permission denied.'}, status=403)
        # Allow riders to preview the route (pickup -> destination) even when no driver has
        # been assigned yet. In that case, we will compute a pickup->destination route
        # and return it with driver coordinates set to null so the frontend draws only
        # the preview route. If a driver exists, return driver info as before.
        try:
            rider_profile = Rider.objects.get(user=request.user)
        except Rider.DoesNotExist:
            return JsonResponse({'status': 'error', 'message': 'Rider profile not found.'}, status=404)

        driver_profile = None
        if booking.driver:
            try:
                driver_profile = Driver.objects.get(user=booking.driver)
            except Driver.DoesNotExist:
                # If driver record is missing, continue without driver info
                driver_profile = None
    else:
        return JsonResponse({'status': 'error', 'message': 'Unauthorized.'}, status=403)
    # Try to include tricycle details if available. The Tricycle model or relation
    # may not exist yet in the codebase, so handle gracefully.
    tricycle_data = None
    try:
        # Prefer explicit Tricycle model if available
        from apps.user.models import Tricycle
        try:
            # Some implementations may link Tricycle to Driver (model instance) or to the CustomUser.
            trike = Tricycle.objects.filter(driver=driver_profile).first()
            if not trike:
                # Try linking by user if different FK was used
                trike = Tricycle.objects.filter(driver__user=driver_profile.user).first()
        except Exception:
            trike = None
        if trike:
            tricycle_data = {
                'plate_number': getattr(trike, 'plate_number', None),
                'color': getattr(trike, 'color', None),
                'image_url': getattr(trike, 'image_url', None),
            }
    except Exception:
        # No Tricycle model present — try to access a related attribute on the driver_profile
        try:
            trike = getattr(driver_profile, 'tricycle', None)
            if trike:
                tricycle_data = {
                    'plate_number': getattr(trike, 'plate_number', None),
                    'color': getattr(trike, 'color', None),
                    'image_url': getattr(trike, 'image_url', None),
                }
        except Exception:
            tricycle_data = None

    # If there's no driver assigned (rider preview), compute pickup->destination route
    route_payload = None
    try:
        if not booking.driver:
            routing_service = RoutingService()
            # Calculate route from pickup to destination (coords expected as lon,lat)
            start = (float(booking.pickup_longitude), float(booking.pickup_latitude))
            end = (float(booking.destination_longitude), float(booking.destination_latitude))
            route_info = routing_service.calculate_route(start, end)
            if route_info:
                route_payload = {
                    'route_data': route_info.get('route_data'),
                    'distance': route_info.get('distance'),
                    'duration': route_info.get('duration'),
                    'too_close': route_info.get('too_close', False)
                }
        else:
            # If a driver exists, the frontend will fetch driver/pickup and pickup/destination as needed
            route_payload = None
    except Exception as e:
        route_payload = None
    # Compute distances for convenience to display in the UI
    pickup_to_dest_km = None
    driver_to_pickup_km = None
    if route_payload:
        try:
            pickup_to_dest_km = route_payload.get('distance')
        except Exception:
            pickup_to_dest_km = None
    else:
        # If driver exists and routing can compute, try to compute distances
        try:
            routing_service = RoutingService()
            if booking.pickup_latitude and booking.pickup_longitude and booking.destination_latitude and booking.destination_longitude:
                pd_start = (float(booking.pickup_longitude), float(booking.pickup_latitude))
                pd_end = (float(booking.destination_longitude), float(booking.destination_latitude))
                pd_info = routing_service.calculate_route(pd_start, pd_end)
                if pd_info:
                    pickup_to_dest_km = pd_info.get('distance')
            if booking.driver and driver_profile and driver_profile.current_latitude and driver_profile.current_longitude and booking.pickup_latitude and booking.pickup_longitude:
                dp_start = (float(driver_profile.current_longitude), float(driver_profile.current_latitude))
                dp_end = (float(booking.pickup_longitude), float(booking.pickup_latitude))
                dp_info = routing_service.calculate_route(dp_start, dp_end)
                if dp_info:
                    driver_to_pickup_km = dp_info.get('distance')
        except Exception:
            pass

    # Driver/tricycle frontend-friendly details
    driver_info = None
    if driver_profile:
        # If the Driver model doesn't have current coords, try to read the real-time
        # DriverLocation (apps.booking.models.DriverLocation) as a fallback source.
        try:
            from apps.booking.models import DriverLocation as _DriverLocation
            dl = _DriverLocation.objects.filter(driver=driver_profile.user).first()
            if dl:
                # Only set if missing on the driver_profile
                if not driver_profile.current_latitude and getattr(dl, 'latitude', None) is not None:
                    driver_profile.current_latitude = dl.latitude
                if not driver_profile.current_longitude and getattr(dl, 'longitude', None) is not None:
                    driver_profile.current_longitude = dl.longitude
        except Exception:
            # Booking app or DriverLocation may not be present; ignore and continue
            pass
        try:
            driver_name = f"{driver_profile.user.first_name} {driver_profile.user.last_name}".strip() or driver_profile.user.username
        except Exception:
            driver_name = getattr(driver_profile.user, 'username', 'Driver')
        driver_info = {
            'id': getattr(driver_profile, 'id', None),
            'name': driver_name,
            'lat': driver_profile.current_latitude,
            'lon': driver_profile.current_longitude,
        }
        # Try to attach tricycle info if not yet included
        if tricycle_data:
            driver_info['plate'] = tricycle_data.get('plate_number')
            driver_info['color'] = tricycle_data.get('color')

    return JsonResponse({
        'status': 'success',
        'booking_status': booking.status,
        'driver': driver_info,
        'driver_lat': driver_profile.current_latitude if driver_profile else None,
        'driver_lon': driver_profile.current_longitude if driver_profile else None,
        'driver_name': driver_info.get('name') if driver_info else None,
        'rider_lat': rider_profile.current_latitude if rider_profile else None,
        'rider_lon': rider_profile.current_longitude if rider_profile else None,
        'pickup_lat': booking.pickup_latitude,
        'pickup_lon': booking.pickup_longitude,
        'destination_lat': booking.destination_latitude,
        'destination_lon': booking.destination_longitude,
        'tricycle': tricycle_data,
        'route_payload': route_payload,
        'pickup_to_destination_km': pickup_to_dest_km,
        'driver_to_pickup_km': driver_to_pickup_km,
    })

@login_required
def get_driver_active_booking(request):
    """Get the active booking for the current driver"""
    if request.user.trikego_user != 'D':
        return JsonResponse({'status': 'error', 'message': 'Only drivers can access this endpoint.'}, status=403)
    
    active_booking = Booking.objects.filter(
        driver=request.user,
        status__in=['accepted', 'on_the_way', 'started']
    ).order_by('-booking_time').first()
    
    if active_booking:
        return JsonResponse({
            'status': 'success',
            'booking_id': active_booking.id,
            'booking_status': active_booking.status
        })
    else:
        return JsonResponse({
            'status': 'success',
            'booking_id': None
        })

