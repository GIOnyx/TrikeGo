from django import forms
from django.contrib.auth.forms import UserCreationForm
from .models import CustomUser, Driver, Rider

class CustomerForm(UserCreationForm):
    class Meta:
        model = CustomUser
        fields = ['username', 'password1', 'password2', 'email', 'first_name', 'last_name']

class DriverRegistrationForm(UserCreationForm):
    license_number = forms.CharField(max_length=20, required=True)
    license_image_url = forms.URLField(required=False, help_text="Optional: URL to your driver's license image")
    
    class Meta:
        model = CustomUser
        fields = ['username', 'password1', 'password2', 'email', 'first_name', 'last_name', 'license_number', 'license_image_url']

class RiderRegistrationForm(UserCreationForm):
    class Meta:
        model = CustomUser
        fields = ['username', 'password1', 'password2', 'email', 'first_name', 'last_name']