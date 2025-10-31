from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status
from django.shortcuts import get_object_or_404

from .models import ChatMessage
from booking.models import Booking


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_messages(request, booking_id):
    """Return messages visible to everyone in the driver's active trip."""
    booking = get_object_or_404(Booking, id=booking_id)

    # Permission: only the rider tied to the booking, or the driver handling it.
    if request.user not in [booking.rider, booking.driver]:
        return Response({'error': 'Permission denied'}, status=status.HTTP_403_FORBIDDEN)

    allowed_statuses = ['accepted', 'on_the_way', 'started']
    if booking.status not in allowed_statuses:
        return Response({'error': 'Chat not available for this booking status'}, status=status.HTTP_403_FORBIDDEN)

    # Determine the current trip scope: all active bookings with the same driver.
    linked_bookings = Booking.objects.filter(
        driver=booking.driver,
        status__in=allowed_statuses
    ) if booking.driver else Booking.objects.filter(id=booking.id)

    messages = (
        ChatMessage.objects.filter(booking__in=linked_bookings)
        .select_related('booking', 'booking__rider', 'booking__driver', 'sender')
        .order_by('timestamp')
    )

    data = []
    for msg in messages:
        sender_display = msg.sender.get_full_name() or msg.sender.username
        trip_driver = msg.booking.driver
        sender_role = 'Driver' if trip_driver and msg.sender_id == trip_driver.id else 'Passenger'
        rider_name = msg.booking.rider.get_full_name() or msg.booking.rider.username if msg.booking.rider else 'Passenger'
        data.append({
            'id': msg.id,
            'message': msg.message,
            'timestamp': msg.timestamp.isoformat(),
            'sender_id': msg.sender.id,
            'sender_username': msg.sender.username,
            'sender_display_name': sender_display,
            'sender_role': sender_role,
            'booking_id': msg.booking_id,
            'booking_label': rider_name,
        })

    return Response({'messages': data})


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def post_message(request, booking_id):
    """Create a message for a booking (only rider or driver may post)."""
    booking = get_object_or_404(Booking, id=booking_id)

    if request.user not in [booking.rider, booking.driver]:
        return Response({'error': 'Permission denied'}, status=status.HTTP_403_FORBIDDEN)

    allowed_statuses = ['accepted', 'on_the_way', 'started']
    if booking.status not in allowed_statuses:
        return Response({'error': 'Chat not available for this booking status'}, status=status.HTTP_403_FORBIDDEN)

    message_text = (request.data.get('message') or '').strip()
    if not message_text:
        return Response({'error': 'Message is required'}, status=status.HTTP_400_BAD_REQUEST)

    msg = ChatMessage.objects.create(
        message=message_text,
        booking=booking,
        sender=request.user
    )

    sender_display = msg.sender.get_full_name() or msg.sender.username
    sender_role = 'Driver' if booking.driver and msg.sender_id == booking.driver.id else 'Passenger'
    rider_name = booking.rider.get_full_name() or booking.rider.username if booking.rider else 'Passenger'

    return Response({
        'id': msg.id,
        'message': msg.message,
        'timestamp': msg.timestamp.isoformat(),
        'sender_id': msg.sender.id,
        'sender_username': msg.sender.username,
        'sender_display_name': sender_display,
        'sender_role': sender_role,
        'booking_id': msg.booking_id,
        'booking_label': rider_name,
    }, status=status.HTTP_201_CREATED)
