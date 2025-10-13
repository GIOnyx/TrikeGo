# booking/forms.py
from django import forms
from .models import Booking
from user.models import CustomUser

class BookingForm(forms.ModelForm):
    # We might not expose rider/driver in a simple form,
    # but handle it in the view based on logged-in user and backend logic.
    # For now, let's focus on the user-inputted parts.

    class Meta:
        model = Booking
        fields = [
            'pickup_address',
            # 'pickup_latitude', # These will likely be set by JS on the frontend
            # 'pickup_longitude',
            'destination_address',
            # 'destination_latitude',
            # 'destination_longitude',
            # 'booking_time', # Will be set automatically by default
        ]
        widgets = {
            'pickup_address': forms.TextInput(attrs={'placeholder': 'Enter pickup location', 'id': 'pickup_location_input'}),
            'destination_address': forms.TextInput(attrs={'placeholder': 'Enter destination', 'id': 'destination_location_input'}),
        }
    
    # You might want to add custom validation or clean methods here
    def clean(self):
        cleaned_data = super().clean()
        # Example: Ensure pickup and destination addresses are different if needed
        return cleaned_data