from django.urls import path
from .import views

app_name='user'

urlpatterns = [
    path('login', views.Login.as_view(), name='login'),
    path('home', views.LoggedIn.as_view(), name='loggedin'),
]