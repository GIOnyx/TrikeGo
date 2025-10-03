from django.contrib.auth.models import AbstractUser
from django.db import models

class CustomUser(AbstractUser):
    USER_TYPES = (
        ('R', 'Rider'),
        ('A', 'Admin'),
        ('D', 'Driver'),
    )
    
    phone = models.CharField(max_length=11, blank=True, null=True)
    trikego_user = models.CharField(max_length=1, choices=USER_TYPES, blank=True, null=True)


class Admin(models.Model):
    user = models.OneToOneField(CustomUser, on_delete=models.CASCADE, related_name='admin_profile')
    position = models.CharField(max_length=100)
    date_hired = models.DateField()
    years_of_service = models.IntegerField()

    def __str__(self):
        return f"Admin: {self.user.username}"


class Driver(models.Model):
    user = models.OneToOneField(CustomUser, on_delete=models.CASCADE, related_name='driver_profile')
    license_number = models.CharField(max_length=20)
    license_expiry = models.DateField()
    date_hired = models.DateField()
    years_of_service = models.IntegerField()
    is_available = models.BooleanField(default=True)
    license_image_url = models.URLField(blank=True, null=True)

    def __str__(self):
        return f"Driver: {self.user.username}"


class Rider(models.Model):
    user = models.OneToOneField(CustomUser, on_delete=models.CASCADE, related_name='rider_profile')
    loyalty_points = models.IntegerField(default=0)

    def __str__(self):
        return f"Rider: {self.user.username}"
