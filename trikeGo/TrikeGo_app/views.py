from django.shortcuts import render, redirect
from django.views import View
from django.contrib.auth import authenticate, login
from django.contrib import messages
from .forms import RideForm 

def landing_page(request):
    eta = None
    msg = None

    if request.method == "POST":
        form = RideForm(request.POST)
        if form.is_valid():
            pickup = form.cleaned_data["pickup"]
            destination = form.cleaned_data["destination"]

            eta = form.get_eta()
            msg = f"A trike will arrive in ~{eta} minutes."
        else:
            msg = "Please enter pickup and destination."
    else:
        form = RideForm()

    return render(request, "TrikeGo_app/landingPage.html", {
        "form": form,
        "eta": eta,
        "msg": msg
    })



