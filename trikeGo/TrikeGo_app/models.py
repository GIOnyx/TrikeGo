from django.db import models
from django.contrib.auth.models import AbstractUser
# Create your models here.

class User(models.Model):
    user_type = (('R', 'Rider'), ('D', 'Driver'))
    first_name = models.CharField(max_length=25, null=False)
    last_name = models.CharField(max_length=25, null=False)
    username = models.CharField(max_length=15, null=False, primary_key=True)
    password = models.CharField(max_length=10, null=False)
    email = models.EmailField(max_length=25, null=False)
    trikego_user = models.CharField(max_length=1, choices=user_type)

class Rider(models.Model):
    loyalty_points = models.IntegerField(default=0)
    

class Driver(models.Model):
    position = models.CharField(max_length=100)
    date_hired = models.DateField()
    years_of_service = models.IntegerField()


