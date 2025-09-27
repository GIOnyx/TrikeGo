from django.shortcuts import render
from .forms import RideForm
from login.models import User, Driver 

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

def passenger_register(request):
    if request.method == "POST":
        # Handle passenger registration form
        full_name = request.POST.get('full_name')
        email = request.POST.get('email')
        phone_number = request.POST.get('phone_number')
        password1 = request.POST.get('password1')
        password2 = request.POST.get('password2')
        
        # Basic validation
        if password1 != password2:
            return render(request, "TrikeGo_app/landingPage.html", {
                "error": "Passwords don't match"
            })
        
        # Split full name into first and last name
        name_parts = full_name.split(' ', 1)
        first_name = name_parts[0]
        last_name = name_parts[1] if len(name_parts) > 1 else ""
        
        # Create username from email (before @)
        username = email.split('@')[0]
        
        try:
            # Create User record for passenger
            user = User.objects.create(
                username=username,
                password=password1,  # In production, hash this password
                email=email,
                first_name=first_name,
                last_name=last_name,
                phone=phone_number,
                trikego_user='M'  # M for Mobile/Passenger
            )
            
            return render(request, "TrikeGo_app/landingPage.html", {
                "success": "Passenger account created successfully!"
            })
        except Exception as e:
            return render(request, "TrikeGo_app/landingPage.html", {
                "error": f"Registration failed: {str(e)}"
            })
    
    return render(request, "TrikeGo_app/landingPage.html")

def driver_register(request):
    if request.method == "POST":
        # Handle driver registration form
        full_name = request.POST.get('full_name')
        email = request.POST.get('email')
        phone_number = request.POST.get('phone_number')
        license_number = request.POST.get('license_number')
        password1 = request.POST.get('password1')
        password2 = request.POST.get('password2')
        
        # Basic validation
        if password1 != password2:
            return render(request, "TrikeGo_app/landingPage.html", {
                "error": "Passwords don't match"
            })
        
        # Split full name into first and last name
        name_parts = full_name.split(' ', 1)
        first_name = name_parts[0]
        last_name = name_parts[1] if len(name_parts) > 1 else ""
        
        # Create username from email (before @)
        username = email.split('@')[0]
        
        try:
            # Create User record for driver
            user = User.objects.create(
                username=username,
                password=password1,  # In production, hash this password
                email=email,
                first_name=first_name,
                last_name=last_name,
                phone=phone_number,
                trikego_user='D'  # D for Driver
            )
            
            # Create Driver record with additional fields
            driver = Driver.objects.create(
                username=user,  # Foreign key to User
                license_number=license_number,
                license_expiry='2025-12-31',  # Default expiry, should be from form
                date_hired='2024-01-01',  # Default hire date, should be current date
                years_of_service=0,
                is_available=True
            )
            
            return render(request, "TrikeGo_app/landingPage.html", {
                "success": "Driver account created successfully!"
            })
        except Exception as e:
            return render(request, "TrikeGo_app/landingPage.html", {
                "error": f"Registration failed: {str(e)}"
            })
    
    return render(request, "TrikeGo_app/landingPage.html")