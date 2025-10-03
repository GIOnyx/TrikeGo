from django.contrib.auth.models import AbstractUser
from django.db import models

class CustomUser(AbstractUser):
    pass


class Admin(models.Model):
    position = models.CharField(max_length=100)
    date_hired = models.DateField()
    years_of_service = models.IntegerField()


class Driver(models.Model):
    user = models.OneToOneField(CustomUser, on_delete=models.CASCADE, related_name='driver_profile')
    license_number = models.CharField(max_length=20)
    license_expiry = models.DateField()
    date_hired = models.DateField()
    years_of_service = models.IntegerField()
    is_available = models.BooleanField(default=True)
    license_image_url = models.URLField(blank=True, null=True)

class Rider(models.Model):
    user = models.OneToOneField(CustomUser, on_delete=models.CASCADE, related_name='rider_profile')
    loyalty_points = models.IntegerField(default=0)