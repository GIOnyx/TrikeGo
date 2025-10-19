from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status
from django.shortcuts import get_object_or_404
from django.utils import timezone
from datetime import timedelta
from decimal import Decimal

from .models import DriverLocation, Booking, RouteSnapshot
from .services import RoutingService


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
    active_booking = Booking.objects.filter(
        driver=request.user,
        status__in=['accepted', 'on_the_way', 'started']
    ).first()
    
    if active_booking:
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