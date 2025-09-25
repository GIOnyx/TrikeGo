from django.contrib.auth.models import AbstractUser
from django.db import models

# Create your models here.
class User(models.Model):
    user_type = (('C', 'Customer'), ('S', 'Staff'))
    username = models.CharField(max_length=15, null=False, primary_key=True)
    password = models.CharField(max_length=10, null=False)
    email = models.EmailField(max_length=25, null=False)
    first_name = models.CharField(max_length=25, null=False)
    last_name = models.CharField(max_length=25, null=False)
    phone = models.CharField(max_length=11, null=False)
    trikego_user = models.CharField(max_length=1, choices=user_type)


class Staff(User):
    position = models.CharField(max_length=100)
    date_hired = models.DateField()
    years_of_service = models.IntegerField()
