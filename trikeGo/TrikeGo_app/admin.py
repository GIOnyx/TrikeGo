from django.contrib import admin
from .models import Rider, Driver, User

# Register your models here.
admin.site.register(User)
admin.site.register(Rider)
admin.site.register(Driver)