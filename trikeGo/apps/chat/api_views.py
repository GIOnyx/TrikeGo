from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status
from django.shortcuts import get_object_or_404

from .models import ChatMessage
from apps.booking.models import Booking


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_messages(request, booking_id):
    """Return messages for a booking (only rider or driver may access)."""
    booking = get_object_or_404(Booking, id=booking_id)

    # Permission: only rider or driver
    if request.user not in [booking.rider, booking.driver]:
        return Response({'error': 'Permission denied'}, status=status.HTTP_403_FORBIDDEN)

    # Chat allowed only while booking is active/ongoing (accepted, on_the_way, started)
    allowed_statuses = ['accepted', 'on_the_way', 'started']
    if booking.status not in allowed_statuses:
        return Response({'error': 'Chat not available for this booking status'}, status=status.HTTP_403_FORBIDDEN)

    messages = ChatMessage.objects.filter(booking=booking).order_by('timestamp')
    data = [
        {
            'id': m.id,
            'message': m.message,
            'timestamp': m.timestamp.isoformat(),
            'sender_id': m.sender.id,
            'sender_username': m.sender.username,
        }
        for m in messages
    ]

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

    return Response({
        'id': msg.id,
        'message': msg.message,
        'timestamp': msg.timestamp.isoformat(),
        'sender_id': msg.sender.id,
        'sender_username': msg.sender.username,
    }, status=status.HTTP_201_CREATED)
