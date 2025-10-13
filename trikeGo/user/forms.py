from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.core.exceptions import ValidationError
from django.core.validators import URLValidator
from .models import CustomUser, Driver, Rider
from django.contrib.auth.forms import AuthenticationForm



import re

class CustomerForm(UserCreationForm):
    email = forms.EmailField(
        required=True,
        widget=forms.EmailInput(attrs={
            'placeholder': 'Enter your email address'
        })
    )
    first_name = forms.CharField(
        max_length=30,
        required=True,
        widget=forms.TextInput(attrs={
            'placeholder': 'First name'
        })
    )
    last_name = forms.CharField(
        max_length=30,
        required=True,
        widget=forms.TextInput(attrs={
            'placeholder': 'Last name'
        })
    )
    phone = forms.CharField(
        max_length=11,
        required=True,
        help_text="Format: 09XXXXXXXXX",
        widget=forms.TextInput(attrs={
            'pattern': r'^09\d{9}$',
            'inputmode': 'numeric',
            'maxlength': '11',
            'placeholder': 'Phone number (09XXXXXXXXX)'
        })
    )
    
    class Meta:
        model = CustomUser
        fields = ['username', 'password1', 'password2', 'email', 'first_name', 'last_name', 'phone']
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['username'].widget.attrs.update({'placeholder': 'Choose a username'})
        self.fields['password1'].widget.attrs.update({'placeholder': 'Enter a password'})
        self.fields['password2'].widget.attrs.update({'placeholder': 'Confirm your password'})

class DriverRegistrationForm(UserCreationForm):
    email = forms.EmailField(
        required=True,
        widget=forms.EmailInput(attrs={
            'placeholder': 'Enter your email address'
        })
    )
    first_name = forms.CharField(
        max_length=30,
        required=True,
        widget=forms.TextInput(attrs={
            'placeholder': 'First name'
        })
    )
    last_name = forms.CharField(
        max_length=30,
        required=True,
        widget=forms.TextInput(attrs={
            'placeholder': 'Last name'
        })
    )
    phone = forms.CharField(
        max_length=11,
        required=True,
        help_text="Format: 09XXXXXXXXX",
        widget=forms.TextInput(attrs={
            'pattern': r'^09\d{9}$',
            'inputmode': 'numeric',
            'maxlength': '11',
            'placeholder': 'Phone number (09XXXXXXXXX)'
        })
    )
    license_number = forms.CharField(
        max_length=11,
        required=True,
        widget=forms.TextInput(attrs={
            'pattern': r'^\d{11}$',
            'inputmode': 'numeric',
            'maxlength': '11',
            'placeholder': "Driver's License Number"
        })
    )
    license_image_url = forms.URLField(
        required=True,
        help_text="URL to your driver's license image (.jpg/.jpeg/.png)",
        widget=forms.URLInput(attrs={
            'pattern': r'^https?://.+\.(jpg|jpeg|png)$',
            'placeholder': 'License Image URL'
        })
    )
    
    class Meta:
        model = CustomUser
        fields = ['username', 'password1', 'password2', 'email', 'first_name', 'last_name', 'phone', 'license_number', 'license_image_url']
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['username'].widget.attrs.update({'placeholder': 'Choose a username'})
        self.fields['password1'].widget.attrs.update({'placeholder': 'Enter a password'})
        self.fields['password2'].widget.attrs.update({'placeholder': 'Confirm your password'})
    
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
    email = forms.EmailField(
        required=True,
        widget=forms.EmailInput(attrs={
            'placeholder': 'Enter your email address'
        })
    )
    first_name = forms.CharField(
        max_length=30,
        required=True,
        widget=forms.TextInput(attrs={
            'placeholder': 'First name'
        })
    )
    last_name = forms.CharField(
        max_length=30,
        required=True,
        widget=forms.TextInput(attrs={
            'placeholder': 'Last name'
        })
    )
    phone = forms.CharField(
        max_length=11,
        required=True,
        help_text="Format: 09XXXXXXXXX",
        widget=forms.TextInput(attrs={
            'pattern': r'^09\d{9}$',
            'inputmode': 'numeric',
            'maxlength': '11',
            'placeholder': 'Phone number (09XXXXXXXXX)'
        })
    )
    
    class Meta:
        model = CustomUser
        fields = ['username', 'password1', 'password2', 'email', 'first_name', 'last_name', 'phone']
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['username'].widget.attrs.update({'placeholder': 'Choose a username'})
        self.fields['password1'].widget.attrs.update({'placeholder': 'Enter a password'})
        self.fields['password2'].widget.attrs.update({'placeholder': 'Confirm your password'})

    # Server-side validations
    def clean_phone(self):
        phone = self.cleaned_data.get('phone', '')
        if not re.match(r'^09\d{9}$', phone):
            raise ValidationError('Phone must be in the format 09XXXXXXXXX')
        return phone

class LoginForm(forms.Form):
    username = forms.CharField(
        max_length=150,
        required=True,
        widget=forms.TextInput(attrs={
            'placeholder': 'Username',
            'required': True
        })
    )
    password = forms.CharField(
        required=True,
        widget=forms.PasswordInput(attrs={
            'placeholder': 'Password',
            'required': True
        })
    )
    remember = forms.BooleanField(
        required=False,
        widget=forms.CheckboxInput(attrs={
            'name': 'remember'
        })
    )

class LoginForm(AuthenticationForm):
    username = forms.CharField(widget=forms.TextInput(attrs={
        'placeholder': 'Username',
        'class': 'form-control'
    }))
    password = forms.CharField(widget=forms.PasswordInput(attrs={
        'placeholder': 'Password',
        'class': 'form-control'
    }))

class DriverVerificationForm(forms.Form):
    driver_id = forms.IntegerField(widget=forms.HiddenInput())
    action = forms.CharField(widget=forms.HiddenInput())

    def clean_action(self):
        action = self.cleaned_data.get('action')
        if action not in ['toggle_verify']:
            raise ValidationError('Invalid action.')
        return action

    def clean_driver_id(self):
        driver_id = self.cleaned_data.get('driver_id')
        try:
            Driver.objects.get(id=driver_id)
        except Driver.DoesNotExist:
            raise ValidationError('Driver does not exist.')
        return driver_id