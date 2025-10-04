from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login
from django.contrib import messages
from django.views import View
from .forms import CustomerForm
from .models import Driver, Rider, CustomUser
from datetime import date

class landing_page(View):
    template_name = 'TrikeGo_app/landingPage.html'

    def get(self, request):
        return render(request, self.template_name)
    

class Login(View):
    template_name = 'TrikeGo_app/landingPage.html'

    def get(self, request):
        return render(request, self.template_name)
    
    def post(self, request):
        username = request.POST.get("username")
        password = request.POST.get("password")
        user = authenticate(request, username=username, password=password)

        if user is not None:
            login(request, user)
            print("DEBUG: username:", user.username, "role:", getattr(user, "trikego_user", None))

            # Redirect based on role
            if getattr(user, 'trikego_user', None) == 'D':
                return redirect('user:driver_dashboard')
            elif getattr(user, 'trikego_user', None) == 'R':
                return redirect('user:rider_dashboard')
            elif getattr(user, 'trikego_user', None) == 'A':
                return redirect('user:admin_dashboard')
            else:
                return redirect("user:logged_in") 
        else:
            messages.error(request, "Invalid username or password")
            return render(request, self.template_name)
    

class register_page(View):
    template_name = 'TrikeGo_app/register.html'

    def get(self, request):
        form = CustomerForm()
        # Get the user_type from URL parameter (e.g., ?type=rider or ?type=driver)
        user_type = request.GET.get('type', 'rider')
        return render(request, self.template_name, {
            'form': form,
            'user_type': user_type
        })

    def post(self, request):
        form = CustomerForm(request.POST)
        user_type = request.POST.get('user_type', 'rider')  # Get from hidden field
        
        if form.is_valid():
            user = form.save(commit=False)
            
            # Set the user type based on registration choice
            if user_type == 'driver':
                user.trikego_user = 'D'
            else:
                user.trikego_user = 'R'
            
            user.save()
            
            # Create corresponding Rider or Driver profile
            if user_type == 'driver':
                Driver.objects.create(
                    user=user,
                    license_number='PENDING',  # Will need to be filled later
                    license_expiry=date.today(),  # Placeholder
                    date_hired=date.today(),
                    years_of_service=0
                )
                messages.success(request, "Driver registration successful! Please log in.")
            else:
                Rider.objects.create(user=user)
                messages.success(request, "Rider registration successful! Please log in.")
            
            return redirect('user:landing')
        
        return render(request, self.template_name, {
            'form': form,
            'user_type': user_type
        })
    

class logged_in(View):
    template_name = 'TrikeGo_app/tempLoggedIn.html'

    def get(self, request):
        if request.user.is_authenticated:
            return render(request, self.template_name)
        else:
            return redirect('user:landing')


class RiderDashboard(View):
    template_name = 'TrikeGo_app/rider_dashboard.html'

    def get(self, request):
        if not request.user.is_authenticated:
            return redirect('user:landing')
        if getattr(request.user, 'trikego_user', None) != 'R':
            return redirect('user:landing')
        return render(request, self.template_name)


class DriverDashboard(View):
    template_name = 'TrikeGo_app/driver_dashboard.html'

    def get(self, request):
        if not request.user.is_authenticated:
            return redirect('user:landing')
        if getattr(request.user, 'trikego_user', None) != 'D':
            return redirect('user:landing')
        return render(request, self.template_name)

class AdminDashboard(View):
    template_name = 'TrikeGo_app/admin_dashboard.html'

    def get(self, request):
        if not request.user.is_authenticated:
            return redirect('user:landing')
        if getattr(request.user, 'trikego_user', None) != 'A':
            return redirect('user:landing')

        # Fetch all drivers and riders
        drivers = Driver.objects.select_related("user").all()
        riders = Rider.objects.select_related("user").all()

        # Alternative: if you want ALL users by role directly from CustomUser
        all_drivers = CustomUser.objects.filter(trikego_user="D")
        all_riders = CustomUser.objects.filter(trikego_user="R")

        return render(request, self.template_name, {
            "drivers": drivers,
            "riders": riders,
            "all_drivers": all_drivers,
            "all_riders": all_riders,
        })
