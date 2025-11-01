import os
import django
import json

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'trikeGo.settings')
django.setup()

from booking.models import Booking
from user.models import Rider
from django.test import RequestFactory
from user.views import get_route_info

# Get a pending booking
booking = Booking.objects.filter(status='pending').first()
if not booking:
    print("No pending bookings found")
    exit()

print(f"\n=== Testing Booking #{booking.id} ===")
print(f"Status: {booking.status}")
print(f"Driver: {booking.driver}")
print(f"Driver ID: {booking.driver_id}")

# Create a fake request from the rider
factory = RequestFactory()
request = factory.get(f'/api/booking/{booking.id}/route_info/')
request.user = booking.rider

# Call the view
response = get_route_info(request, booking.id)

# Parse response
data = json.loads(response.content)
print(f"\n=== API Response ===")
print(f"Status: {data.get('status')}")
print(f"Booking Status: {data.get('booking_status')}")
print(f"Driver Lat: {data.get('driver_lat')}")
print(f"Driver Lon: {data.get('driver_lon')}")
print(f"Driver: {data.get('driver')}")
print(f"Fare: {data.get('fare')}")
print(f"Fare Display: {data.get('fare_display')}")
