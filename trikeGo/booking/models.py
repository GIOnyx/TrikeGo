# booking/models.py
from django.db import models
from user.models import CustomUser # Assuming CustomUser is in the 'user' app
from django.utils import timezone

class Booking(models.Model):
    # Foreign Keys to CustomUser
    rider = models.ForeignKey(
        CustomUser,
        on_delete=models.CASCADE,
        related_name='rider_bookings',
        limit_choices_to={'user_type': 'rider'}
    )
    driver = models.ForeignKey(
        CustomUser,
        on_delete=models.SET_NULL, # Driver might not be assigned immediately or could change
        null=True, blank=True,
        related_name='driver_bookings',
        limit_choices_to={'user_type': 'driver'}
    )

    # Location fields (more robust than just varchar)
    pickup_address = models.CharField(max_length=255)
    pickup_latitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    pickup_longitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)

    destination_address = models.CharField(max_length=255)
    destination_latitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    destination_longitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)

    # Booking status (similar to Uber's states)
    STATUS_CHOICES = [
        ('pending', 'Pending Driver Assignment'),
        ('accepted', 'Driver Accepted'),
        ('on_the_way', 'Driver On The Way'),
        ('started', 'Trip Started'),
        ('completed', 'Completed'),
        ('cancelled_by_rider', 'Cancelled by Rider'),
        ('cancelled_by_driver', 'Cancelled by Driver'),
        ('no_driver_found', 'No Driver Found'),
    ]
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')

    booking_time = models.DateTimeField(default=timezone.now)
    start_time = models.DateTimeField(null=True, blank=True)
    end_time = models.DateTimeField(null=True, blank=True)

    fare = models.DecimalField(max_digits=6, decimal_places=2, null=True, blank=True) # For estimated or final fare

    # booking_id is auto-generated primary key by Django usually,
    # so you might not need an explicit 'booking_id' field unless it's a specific requirement.
    # If booking_id in your image is the primary key, Django handles it as `id`.

    def __str__(self):
        return f"Booking {self.id} - {self.rider.username} to {self.destination_address}"

    @property
    def is_active(self):
        return self.status in ['pending', 'accepted', 'on_the_way', 'started']