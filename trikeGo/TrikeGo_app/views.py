from django.shortcuts import render, redirect
from django.views import View
from django.contrib.auth import authenticate, login
from django.contrib import messages
from .forms import CustomerForm
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

def login(request):
    if request.method == "POST":
        username = request.POST.get("username")
        password = request.POST.get("password")

        user = authenticate(request, username=username, password=password)

        if user is not None:
            login(request, user)
            return redirect("TrikeGo_app/landing") 
        else:
            messages.error(request, "Invalid username or password")

    return render(request, "TrikeGo_app/landing.html")

def register_page(request):
    template_name = 'TrikeGo_app/register.html'

    def get(self, request):
        form = CustomerForm()
        return render(request, self.template_name,{'form': form})

    def post(self, request):
        customer = CustomerForm(request.POST)
        if customer.is_valid():
            customer.save()
            return redirect('user:login')
    return render(request, "TrikeGo_app/register.html")
