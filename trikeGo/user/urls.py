from django.urls import path
from . import views

app_name = 'user'

urlpatterns = [
    path('', views.LandingPage.as_view(), name='landing'),

    # Authentication
    path('login/', views.Login.as_view(), name='login'),
    path('register/', views.RegisterPage.as_view(), name='register'),
    path('logged_in/', views.LoggedIn.as_view(), name='logged_in'),

    # Dashboards
    path('rider_dashboard/', views.RiderDashboard.as_view(), name='rider_dashboard'),
    path('driver_dashboard/', views.DriverDashboard.as_view(), name='driver_dashboard'),
    path('trike-admin/dashboard/', views.AdminDashboard.as_view(), name='admin_dashboard'),
]
