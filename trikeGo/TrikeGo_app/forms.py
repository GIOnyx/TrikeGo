from django.forms import ModelForm
from django import forms
from django.contrib.auth.forms import AuthenticationForm
import random
from .models import User

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


class UserForm(ModelForm):
    username = forms.CharField(widget=forms.TextInput(attrs={'placeholder': 'Username'}))
    password = forms.CharField(widget=forms.PasswordInput(attrs={'placeholder': 'Password'}))
    email = forms.EmailField(widget=forms.EmailInput(attrs={'placeholder': 'Email'}))
    trikeGo_user = forms.CharField(initial='C', widget=forms.HiddenInput())

    class Meta:
        model = User
        fields = ['username', 'password', 'email', 'trikeGo_user']