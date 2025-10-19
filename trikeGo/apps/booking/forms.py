from django import forms
from .models import Booking
import math

class BookingForm(forms.ModelForm):
    class Meta:
        model = Booking
        fields = [
            'pickup_address',
            'pickup_latitude',
            'pickup_longitude',
            'destination_address',
            'destination_latitude',
            'destination_longitude',
        ]
        widgets = {
            'pickup_address': forms.TextInput(attrs={
                'placeholder': 'Enter pickup location',
                'id': 'pickup_location_input',
                'class': 'autocomplete-input',
                'autocomplete': 'off'
            }),
            'destination_address': forms.TextInput(attrs={
                'placeholder': 'Enter destination',
                'id': 'destination_location_input',
                'class': 'autocomplete-input',
                'autocomplete': 'off'
            }),
            'pickup_latitude': forms.HiddenInput(),
            'pickup_longitude': forms.HiddenInput(),
            'destination_latitude': forms.HiddenInput(),
            'destination_longitude': forms.HiddenInput(),
        }
    
    def clean(self):
        cleaned_data = super().clean()
        pickup = cleaned_data.get('pickup_address')
        destination = cleaned_data.get('destination_address')
        pickup_lat = cleaned_data.get('pickup_latitude')
        pickup_lon = cleaned_data.get('pickup_longitude')
        dest_lat = cleaned_data.get('destination_latitude')
        dest_lon = cleaned_data.get('destination_longitude')
        
        # Check if addresses are identical
        if pickup and destination and pickup == destination:
            raise forms.ValidationError('Pickup and destination must be different locations.')
        
        # Check if coordinates are too close (less than 50 meters)
        if all([pickup_lat, pickup_lon, dest_lat, dest_lon]):
            distance = self._calculate_distance(
                float(pickup_lat), float(pickup_lon),
                float(dest_lat), float(dest_lon)
            )
            
            if distance < 50:  # Less than 50 meters
                raise forms.ValidationError(
                    f'Pickup and destination are too close ({distance:.0f}m apart). '
                    'Please select locations at least 50 meters apart.'
                )
        
        return cleaned_data
    
    def _calculate_distance(self, lat1, lon1, lat2, lon2):
        """Calculate distance between two points in meters using Haversine formula"""
        R = 6371000  # Earth's radius in meters
        
        phi1 = math.radians(lat1)
        phi2 = math.radians(lat2)
        delta_phi = math.radians(lat2 - lat1)
        delta_lambda = math.radians(lon2 - lon1)
        
        a = math.sin(delta_phi/2)**2 + math.cos(phi1) * math.cos(phi2) * math.sin(delta_lambda/2)**2
        c = 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))
        
        return R * c