from django import forms
from django.contrib.auth.forms import UserCreationForm
from .models import CustomUser

class CustomerForm(UserCreationForm):

    class Meta:
        model = CustomUser
        fields = ['username', 'password1', 'password2', 'email', 'first_name', 'last_name']

        #, 'phone', 'trikego_user'