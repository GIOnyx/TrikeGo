from django.contrib import admin
from .models import Driver, Admin, Rider

# Register your models here.
admin.site.register(Admin)
admin.site.register(Driver)
admin.site.register(Rider)