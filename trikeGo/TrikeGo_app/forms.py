from django import forms
import random

class RideForm(forms.Form):
    pickup = forms.CharField(
        max_length=200,
        required=True,
        widget=forms.TextInput(attrs={"placeholder": "Enter pickup location"})
    )
    destination = forms.CharField(
        max_length=200,
        required=True,
        widget=forms.TextInput(attrs={"placeholder": "Where to?"})
    )

    def get_eta(self):
        """Return a random ETA in minutes."""
        return random.randint(2, 7)
