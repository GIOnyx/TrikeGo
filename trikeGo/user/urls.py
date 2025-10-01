from django.urls import path
from . import views

app_name='user'

urlpatterns = [
    path('', views.landing_page.as_view(), name='landing'),
    path("login/", views.Login.as_view(), name="login"),
    path('register/', views.register_page.as_view(), name='register'),
    path('logged_in/', views.logged_in.as_view(), name='logged_in'),
]