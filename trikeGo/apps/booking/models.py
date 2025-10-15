# In apps/booking/models.py

from django.db import models
from apps.user.models import CustomUser 
from django.utils import timezone

class Booking(models.Model):
    rider = models.ForeignKey(
        CustomUser,
        on_delete=models.CASCADE,
        related_name='rider_bookings',
        limit_choices_to={'trikego_user': 'R'}
    )
    driver = models.ForeignKey(
        CustomUser,
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='driver_bookings',
        limit_choices_to={'trikego_user': 'D'}
    )

    # Location fields
    pickup_address = models.CharField(max_length=255)
    pickup_latitude = models.DecimalField(max_digits=18, decimal_places=15, null=True, blank=True)
    pickup_longitude = models.DecimalField(max_digits=18, decimal_places=15, null=True, blank=True)

    destination_address = models.CharField(max_length=255)
    destination_latitude = models.DecimalField(max_digits=18, decimal_places=15, null=True, blank=True)
    destination_longitude = models.DecimalField(max_digits=18, decimal_places=15, null=True, blank=True)

    # ... (rest of the model is the same)
    STATUS_CHOICES = [
        ('pending', 'Pending Driver Assignment'),
        # ... other choices
    ]
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    booking_time = models.DateTimeField(default=timezone.now)
    start_time = models.DateTimeField(null=True, blank=True)
    end_time = models.DateTimeField(null=True, blank=True)
    fare = models.DecimalField(max_digits=6, decimal_places=2, null=True, blank=True)

    def __str__(self):
        return f"Booking {self.id} - {self.rider.username} to {self.destination_address}"

    @property
    def is_active(self):
        return self.status in ['pending', 'accepted', 'on_the_way', 'started']