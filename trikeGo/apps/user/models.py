from django.contrib.auth.models import AbstractUser
from django.db import models

class CustomUser(AbstractUser):
    USER_TYPES = (
        ('R', 'Rider'),
        ('A', 'Admin'),
        ('D', 'Driver'),
    )
    
    phone = models.CharField(max_length=20, blank=True, null=True)
    trikego_user = models.CharField(max_length=1, choices=USER_TYPES, default='R')


class Admin(models.Model):
    user = models.OneToOneField(CustomUser, on_delete=models.CASCADE, null=True, blank=True)
    position = models.CharField(max_length=100)
    date_hired = models.DateField()
    years_of_service = models.IntegerField()


class Driver(models.Model):
    user = models.OneToOneField(CustomUser, on_delete=models.CASCADE, null=True, blank=True)
    license_number = models.CharField(max_length=11)
    license_image_url = models.URLField(blank=True, null=True)
    license_expiry = models.DateField()
    date_hired = models.DateField()
    years_of_service = models.IntegerField()
    STATUS_CHOICES = (
        ('Offline', 'Offline'),
        ('Online', 'Online'),
        ('In_trip', 'In trip'),
    )
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='Offline')
    is_verified = models.BooleanField(default=False)
    current_latitude = models.DecimalField(max_digits=18, decimal_places=15, null=True, blank=True)
    current_longitude = models.DecimalField(max_digits=18, decimal_places=15, null=True, blank=True)

class Rider(models.Model):
    user = models.OneToOneField(CustomUser, on_delete=models.CASCADE, null=True, blank=True)
    loyalty_points = models.IntegerField(default=0)
    # --- NEW FIELDS FOR RIDER TRACKING ---
    current_latitude = models.DecimalField(max_digits=18, decimal_places=15, null=True, blank=True)
    current_longitude = models.DecimalField(max_digits=18, decimal_places=15, null=True, blank=True)

