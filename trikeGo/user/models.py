from django.contrib.auth.models import AbstractUser
from django.db import models

class CustomUser(AbstractUser):
    USER_TYPES = (
        ('R', 'Rider'),
        ('A', 'Admin'),
        ('D', 'Driver'),
    )

# Create your models here.
    #phone = models.CharField(max_length=11, null=False)
    #trikego_user = models.CharField(max_length=1, choices=USER_TYPES)


class Admin(models.Model):
    position = models.CharField(max_length=100)
    date_hired = models.DateField()
    years_of_service = models.IntegerField()


class Driver(models.Model):
    license_number = models.CharField(max_length=20)
    license_expiry = models.DateField()
    date_hired = models.DateField()
    years_of_service = models.IntegerField()
    is_available = models.BooleanField(default=True)

class Rider(models.Model):
    loyalty_points = models.IntegerField(default=0)