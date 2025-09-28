from django.forms import ModelForm
from django import forms
from .models import Customer

class CustomerForm(ModelForm):
    username = forms.CharField(widget=forms.TextInput(attrs={'placeholder': 'Username'}))
    password = forms.CharField(widget=forms.PasswordInput(attrs={'placeholder': 'Password'}))
    email = forms.EmailField(widget=forms.EmailInput(attrs={'placeholder': 'Email'}))
    first_name = forms.CharField(widget=forms.TextInput(attrs={'placeholder': 'First Name'}))
    last_name = forms.CharField(widget=forms.TextInput(attrs={'placeholder': 'Last Name'}))
    phone = forms.CharField(widget=forms.TextInput(attrs={'placeholder': 'Phone Number'}))
    trikego_user = forms.CharField(initial='C', widget=forms.HiddenInput())

    class Meta:
        model = Customer
        fields = ['username', 'password', 'email', 'first_name', 'last_name', 'phone', 'trikego_user']