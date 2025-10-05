from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.core.exceptions import ValidationError
from .models import CustomUser, Driver, Rider
import re

class CustomerForm(UserCreationForm):
    class Meta:
        model = CustomUser
        fields = ['username', 'password1', 'password2', 'email', 'first_name', 'last_name', 'phone']

class DriverRegistrationForm(UserCreationForm):
    phone = forms.CharField(
        max_length=11,
        required=True,
        help_text="Format: 09XXXXXXXXX",
        widget=forms.TextInput(attrs={
            'pattern': r'^09\\d{9}$',
            'inputmode': 'numeric',
            'maxlength': '11',
            'placeholder': 'Phone number (09XXXXXXXXX)'
        })
    )
    license_number = forms.CharField(
        max_length=11,
        required=True,
        widget=forms.TextInput(attrs={
            'pattern': r'^\\d{11}$',
            'inputmode': 'numeric',
            'maxlength': '11',
            'placeholder': "Driver's License Number"
        })
    )
    license_image_url = forms.URLField(
        required=True,
        help_text="URL to your driver's license image (.jpg/.jpeg/.png)",
        widget=forms.URLInput(attrs={
            'pattern': r'^https?://.+\\.(jpg|jpeg|png)$',
            'placeholder': 'License Image URL'
        })
    )
    
    class Meta:
        model = CustomUser
        fields = ['username', 'password1', 'password2', 'email', 'first_name', 'last_name', 'phone', 'license_number', 'license_image_url']
    
    # Server-side validations
    def clean_phone(self):
        phone = self.cleaned_data.get('phone', '')
        if not re.match(r'^09\d{9}$', phone):
            raise ValidationError('Phone must be in the format 09XXXXXXXXX')
        return phone

    def clean_license_number(self):
        license_number = self.cleaned_data.get('license_number', '')
        if not re.match(r'^\d{11}$', license_number):
            raise ValidationError("License number must be 11 digits")
        return license_number

    def clean_license_image_url(self):
        url = self.cleaned_data.get('license_image_url', '')
        validator = URLValidator(schemes=['http', 'https'])
        try:
            validator(url)
        except ValidationError:
            raise ValidationError('License image URL must be a valid HTTP/HTTPS URL')
        return url

class RiderRegistrationForm(UserCreationForm):
    phone = forms.CharField(
        max_length=11,
        required=True,
        help_text="Format: 09XXXXXXXXX",
        widget=forms.TextInput(attrs={
            'pattern': r'^09\\d{9}$',
            'inputmode': 'numeric',
            'maxlength': '11',
            'placeholder': 'Phone number (09XXXXXXXXX)'
        })
    )
    class Meta:
        model = CustomUser
        fields = ['username', 'password1', 'password2', 'email', 'first_name', 'last_name', 'phone']

    # Server-side validations
    def clean_phone(self):
        phone = self.cleaned_data.get('phone', '')
        if not re.match(r'^09\d{9}$', phone):
            raise ValidationError('Phone must be in the format 09XXXXXXXXX')
        return phone

# end DriverRegistrationForm