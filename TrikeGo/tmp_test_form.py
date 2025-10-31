import sys, os
sys.path.insert(0, '.')
os.environ.setdefault('DJANGO_SETTINGS_MODULE','trikeGo.settings')
import django
django.setup()
from booking.forms import BookingForm

data = {
 'pickup_address':'A',
 'pickup_latitude':'14.5995',
 'pickup_longitude':'120.9842',
 'destination_address':'B',
 'destination_latitude':'14.6030',
 'destination_longitude':'120.9842',
 'passengers':'2',
}
form = BookingForm(data=data)
print('is_valid=', form.is_valid())
print('errors=', form.errors)
