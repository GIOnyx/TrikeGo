from django.urls import path
from . import views

urlpatterns = [
    path("", views.landing_page, name="landing"),
    path("login.html", views.login_page, name="login_html"),
    path("login/", views.login_page, name="login"),
    path("register/", views.register_page, name="register"),
    path("passenger/register/", views.passenger_register, name="passenger_register"),
    path("driver/register/", views.driver_register, name="driver_register"),
]
