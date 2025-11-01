import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'trikeGo.settings')
django.setup()

from user.models import Driver

drivers = Driver.objects.all()
print(f'Total drivers: {drivers.count()}')

for d in drivers:
    lat = d.current_latitude
    lon = d.current_longitude
    username = d.user.username if d.user else f'driver_{d.id}'
    
    if lat is None or lon is None:
        print(f'{username}: lat={lat}, lon={lon} (NULL coordinates)')
    elif abs(float(lat)) < 1 or abs(float(lon)) < 1:
        print(f'{username}: lat={lat}, lon={lon} (NEAR ZERO - Africa region!)')
    else:
        print(f'{username}: lat={lat}, lon={lon}')
