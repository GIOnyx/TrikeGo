from django.db import models

from TrikeGo_app.models import Rider, Driver

# Create your models here.
class Booking(models.Model):
    booking_id = models.AutoField(primary_key=True)
    rider = models.ForeignKey(Rider, on_delete=models.CASCADE)
    driver = models.ForeignKey(Driver, on_delete=models.CASCADE, null=True, blank=True)
    pickup_location = models.CharField(max_length=200)
    destination = models.CharField(max_length=200)
    booking_time = models.DateTimeField(auto_now_add=True)
    is_completed = models.BooleanField(default=False)

class Payment(models.Model):
    payment_id = models.AutoField(primary_key=True)
    booking = models.ForeignKey(Booking, on_delete=models.CASCADE)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    payment_time = models.DateTimeField(auto_now_add=True)
    payment_method = models.CharField(max_length=50)

class Cancellation(models.Model):
    cancellation_id = models.AutoField(primary_key=True)
    booking = models.ForeignKey(Booking, on_delete=models.CASCADE)
    reason = models.TextField()
    cancellation_time = models.DateTimeField(auto_now_add=True)