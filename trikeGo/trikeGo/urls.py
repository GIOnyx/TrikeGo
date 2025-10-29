"""
URL configuration for trikeGo project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
# In trikeGo/trikeGo/urls.py

# In trikeGo/trikeGo/urls.py

from django.contrib import admin
from django.urls import path, include

urlpatterns = [
    # Core Django URLs
    path('admin/', admin.site.urls),
    path('accounts/', include('django.contrib.auth.urls')),

    # Your App URLs
    path('booking/', include('booking.urls')),  # Handles all URLs starting with /booking/
    path('', include('user.urls')),  # Handles user-related URLs like login, dashboards, etc.
    # Chat API and views
    path('chat/', include('chat.urls')),
]