from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status
from django.shortcuts import get_object_or_404
from django.utils import timezone
from datetime import timedelta
from decimal import Decimal

from .models import DriverLocation, Booking, RouteSnapshot, BookingStop
from .services import RoutingService
from .utils import build_driver_itinerary, ensure_booking_stops, plan_driver_stops, calculate_distance
from user.models import Driver, Rider


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def update_driver_location(request):
    """Update driver's current location"""
    if request.user.trikego_user != 'D':
        return Response({'error': 'Only drivers can update location'}, status=status.HTTP_403_FORBIDDEN)
    
    latitude = request.data.get('latitude')
    longitude = request.data.get('longitude')
    heading = request.data.get('heading')
    speed = request.data.get('speed')
    accuracy = request.data.get('accuracy')
    
    if not latitude or not longitude:
        return Response({'error': 'Latitude and longitude required'}, status=status.HTTP_400_BAD_REQUEST)
    
    # Update or create driver location
    location, created = DriverLocation.objects.update_or_create(
        driver=request.user,
        defaults={
            'latitude': Decimal(str(latitude)),
            'longitude': Decimal(str(longitude)),
            'heading': Decimal(str(heading)) if heading else None,
            'speed': Decimal(str(speed)) if speed else None,
            'accuracy': Decimal(str(accuracy)) if accuracy else None,
        }
    )
    
    # Check for active bookings and reroute if needed
    active_bookings = Booking.objects.filter(
        driver=request.user,
        status__in=['accepted', 'on_the_way', 'started']
    )

    for active_booking in active_bookings:
        check_and_reroute(active_booking, location)
    
    return Response({
        'status': 'success',
        'location': {
            'latitude': float(location.latitude),
            'longitude': float(location.longitude),
            'timestamp': location.timestamp.isoformat()
        }
    })


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_driver_location(request, booking_id):
    """Get driver's current location for a booking"""
    booking = get_object_or_404(Booking, id=booking_id)
    
    # Check permissions
    if request.user not in [booking.rider, booking.driver]:
        return Response({'error': 'Permission denied'}, status=status.HTTP_403_FORBIDDEN)
    
    if not booking.driver:
        return Response({'error': 'No driver assigned'}, status=status.HTTP_404_NOT_FOUND)
    
    try:
        location = DriverLocation.objects.get(driver=booking.driver)
        
        # Calculate ETA if rider is requesting
        eta_seconds = None
        if request.user == booking.rider:
            routing_service = RoutingService()
            
            if booking.status == 'accepted' or booking.status == 'on_the_way':
                # ETA to pickup
                destination = (float(booking.pickup_longitude), float(booking.pickup_latitude))
            else:
                # ETA to destination
                destination = (float(booking.destination_longitude), float(booking.destination_latitude))
            
            eta_seconds = routing_service.get_eta(location, destination)
        
        return Response({
            'latitude': float(location.latitude),
            'longitude': float(location.longitude),
            'heading': float(location.heading) if location.heading else None,
            'speed': float(location.speed) if location.speed else None,
            'timestamp': location.timestamp.isoformat(),
            'eta_seconds': eta_seconds
        })
    except DriverLocation.DoesNotExist:
        return Response({'error': 'Driver location not available'}, status=status.HTTP_404_NOT_FOUND)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_current_route(request, booking_id):
    """Get current active route for a booking"""
    booking = get_object_or_404(Booking, id=booking_id)
    
    # Check permissions
    if request.user not in [booking.rider, booking.driver]:
        return Response({'error': 'Permission denied'}, status=status.HTTP_403_FORBIDDEN)
    
    route = RouteSnapshot.objects.filter(booking=booking, is_active=True).first()
    
    if not route:
        return Response({'error': 'No active route found'}, status=status.HTTP_404_NOT_FOUND)
    
    return Response({
        'route_data': route.route_data,
        'distance': float(route.distance),
        'duration': route.duration,
        'created_at': route.created_at.isoformat()
    })


def check_and_reroute(booking, driver_location):
    """Check if rerouting is needed and perform reroute"""
    routing_service = RoutingService()
    
    # Get current active route
    current_route = RouteSnapshot.objects.filter(booking=booking, is_active=True).first()
    
    # Check if rerouting is needed
    if routing_service.should_reroute(driver_location, current_route):
        print(f"Rerouting needed for booking {booking.id}")
        
        # Determine destination based on status
        if booking.status in ['accepted', 'on_the_way']:
            destination = (float(booking.pickup_longitude), float(booking.pickup_latitude))
        else:
            destination = (float(booking.destination_longitude), float(booking.destination_latitude))
        
        # Calculate new route
        start = (float(driver_location.longitude), float(driver_location.latitude))
        new_route = routing_service.calculate_route(start, destination)
        
        if new_route:
            # Save new route
            routing_service.save_route_snapshot(booking, new_route)
            
            # Update booking estimates
            booking.estimated_distance = Decimal(str(new_route['distance']))
            booking.estimated_duration = new_route['duration'] // 60  # Convert to minutes
            booking.estimated_arrival = timezone.now() + timedelta(seconds=new_route['duration'])
            booking.save()
            
            print(f"New route saved. Distance: {new_route['distance']}km, Duration: {new_route['duration']}s")


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def manual_reroute(request, booking_id):
    """Manually trigger a reroute"""
    booking = get_object_or_404(Booking, id=booking_id)
    
    if request.user != booking.driver:
        return Response({'error': 'Only the assigned driver can reroute'}, status=status.HTTP_403_FORBIDDEN)
    
    try:
        location = DriverLocation.objects.get(driver=request.user)
        check_and_reroute(booking, location)
        
        return Response({'status': 'success', 'message': 'Route recalculated'})
    except DriverLocation.DoesNotExist:
        return Response({'error': 'Driver location not available'}, status=status.HTTP_404_NOT_FOUND)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def driver_itinerary(request):
    """Return the consolidated itinerary for the authenticated driver."""
    if request.user.trikego_user != 'D':
        return Response({'error': 'Only drivers can access the itinerary.'}, status=status.HTTP_403_FORBIDDEN)

    active_bookings = Booking.objects.filter(
        driver=request.user,
        status__in=['accepted', 'on_the_way', 'started']
    )

    for booking in active_bookings:
        ensure_booking_stops(booking)

    payload = build_driver_itinerary(request.user)
    return Response(payload)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def complete_itinerary_stop(request):
    """Mark a specific itinerary stop as completed and refresh the driver's itinerary."""
    if request.user.trikego_user != 'D':
        return Response({'error': 'Only drivers can update itinerary stops.'}, status=status.HTTP_403_FORBIDDEN)

    stop_id = request.data.get('stopId') or request.data.get('stop_id')
    if not stop_id:
        return Response({'error': 'stopId is required.'}, status=status.HTTP_400_BAD_REQUEST)

    try:
        stop = BookingStop.objects.select_related('booking', 'booking__rider').get(
            stop_uid=stop_id,
            booking__driver=request.user,
            booking__status__in=['accepted', 'on_the_way', 'started']
        )
    except BookingStop.DoesNotExist:
        return Response({'error': 'Stop not found or already completed.'}, status=status.HTTP_404_NOT_FOUND)

    if stop.status == 'COMPLETED':
        return Response({'status': 'success', 'message': 'Stop already completed.', 'itinerary': build_driver_itinerary(request.user)['itinerary']})

    # Check if driver is within 10 meters of the stop location
    try:
        driver_profile = Driver.objects.get(user=request.user)
        driver_lat = driver_profile.current_latitude
        driver_lon = driver_profile.current_longitude
        stop_lat = stop.latitude
        stop_lon = stop.longitude
        
        if driver_lat and driver_lon and stop_lat and stop_lon:
            distance_km = calculate_distance(
                float(driver_lat), float(driver_lon),
                float(stop_lat), float(stop_lon)
            )
            distance_meters = distance_km * 1000
            
            if distance_meters > 10:
                return Response({
                    'error': f'You must be within 10 meters of the {stop.stop_type.lower()} location. You are currently {distance_meters:.1f}m away.',
                    'distance': distance_meters,
                    'required': 10
                }, status=status.HTTP_400_BAD_REQUEST)
    except Driver.DoesNotExist:
        pass  # If driver profile doesn't exist, skip proximity check
    except Exception as e:
        print(f"Proximity check error: {e}")
        pass  # Don't block on proximity check errors

    stop.status = 'COMPLETED'
    stop.completed_at = timezone.now()
    stop.save(update_fields=['status', 'completed_at', 'updated_at'])

    booking = stop.booking

    if stop.stop_type == 'PICKUP':
        if booking.status != 'started':
            booking.status = 'started'
            booking.start_time = booking.start_time or timezone.now()
            booking.save(update_fields=['status', 'start_time'])
    else:  # dropoff
        booking.status = 'completed'
        booking.end_time = timezone.now()
        booking.save(update_fields=['status', 'end_time'])

        # Reset rider availability
        Rider.objects.filter(user=booking.rider).update(status='Available')

    # If all bookings completed, set driver status to online
    remaining_stops = BookingStop.objects.filter(
        booking__driver=request.user,
        status__in=['UPCOMING', 'CURRENT'],
        booking__status__in=['accepted', 'on_the_way', 'started']
    )

    if remaining_stops.exists():
        Driver.objects.filter(user=request.user).update(status='In_trip')
    else:
        Driver.objects.filter(user=request.user).update(status='Online')

    # Ensure pick/drop pair consistency – if dropoff completed, mark booking rider status handled above
    plan_driver_stops(request.user)

    payload = build_driver_itinerary(request.user)
    return Response(payload)
    
