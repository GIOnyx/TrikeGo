from django.urls import path
from . import views

urlpatterns = [
    path("", views.landing_page, name="landing"),
    path("login/", views.login_page, name="login"),
    path("register/", views.register_page, name="register"),
]
