from django.shortcuts import render
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

def login_page(request):
    return render(request, "TrikeGo_app/login.html")

def register_page(request):
    return render(request, "TrikeGo_app/register.html")
