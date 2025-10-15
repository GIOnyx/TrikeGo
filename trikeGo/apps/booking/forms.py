from django import forms
from .models import Booking

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
        
        if pickup and destination and pickup == destination:
            raise forms.ValidationError('Pickup and destination must be different locations.')
        
        return cleaned_data