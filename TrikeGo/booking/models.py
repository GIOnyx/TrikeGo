from django.db import models
from user.models import CustomUser 
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

    STATUS_CHOICES = [
        ('pending', 'Pending Driver Assignment'),
        ('accepted', 'Driver Accepted'),
        ('on_the_way', 'Driver On The Way'),
        ('started', 'Trip Started'),
        ('completed', 'Completed'),
        ('cancelled_by_rider', 'Cancelled by Rider'),
        ('cancelled_by_driver', 'Cancelled by Driver'),
        ('no_driver_found', 'No Driver Found')
    ]
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    booking_time = models.DateTimeField(default=timezone.now)
    start_time = models.DateTimeField(null=True, blank=True)
    end_time = models.DateTimeField(null=True, blank=True)
    fare = models.DecimalField(max_digits=6, decimal_places=2, null=True, blank=True)
    
    # Estimated values
    estimated_distance = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)  # in km
    estimated_duration = models.IntegerField(null=True, blank=True)  # in minutes
    estimated_arrival = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return f"Booking {self.id} - {self.rider.username} to {self.destination_address}"

    @property
    def is_active(self):
        return self.status in ['pending', 'accepted', 'on_the_way', 'started']

    class Meta:
        indexes = [
            models.Index(fields=['status']),
            models.Index(fields=['driver']),
            models.Index(fields=['rider']),
            models.Index(fields=['booking_time']),
            models.Index(fields=['driver', 'status']),
        ]


class DriverLocation(models.Model):
    """Track real-time driver locations"""
    driver = models.OneToOneField(
        CustomUser,
        on_delete=models.CASCADE,
        related_name='current_location',
        limit_choices_to={'trikego_user': 'D'}
    )
    latitude = models.DecimalField(max_digits=18, decimal_places=15)
    longitude = models.DecimalField(max_digits=18, decimal_places=15)
    heading = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)  # Direction in degrees
    speed = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)  # Speed in km/h
    accuracy = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)  # in meters
    timestamp = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = "Driver Location"
        verbose_name_plural = "Driver Locations"
    
    def __str__(self):
        return f"{self.driver.username} at ({self.latitude}, {self.longitude})"


class RouteSnapshot(models.Model):
    """Store route snapshots for rerouting and history"""
    booking = models.ForeignKey(Booking, on_delete=models.CASCADE, related_name='routes')
    route_data = models.JSONField()  # Store GeoJSON route data
    distance = models.DecimalField(max_digits=10, decimal_places=2)  # in km
    duration = models.IntegerField()  # in seconds
    created_at = models.DateTimeField(auto_now_add=True)
    is_active = models.BooleanField(default=True)
    
    class Meta:
        ordering = ['-created_at']
    
    def __str__(self):
        return f"Route for Booking {self.booking.id} at {self.created_at}"