from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login
from django.contrib import messages
from django.views import View
from .forms import CustomerForm, DriverRegistrationForm, RiderRegistrationForm
from .models import Rider, Driver, Admin
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
            # Redirect based on user role
            if user.trikego_user == 'D':
                return redirect("user:driver_dashboard")
            elif user.trikego_user == 'R':
                return redirect("user:rider_dashboard")
            elif user.trikego_user == 'A':
                return redirect("user:admin_dashboard")
            else:
                # Fallback for users without role
                return redirect("user:logged_in")
        else:
            messages.error(request, "Invalid username or password")
            return render(request, self.template_name)
    

class register_page(View):
    template_name = 'TrikeGo_app/register.html'

    def get(self, request):
        # Get the user_type from URL parameter (e.g., ?type=rider or ?type=driver)
        user_type = request.GET.get('type', 'rider')
        
        if user_type == 'driver':
            form = DriverRegistrationForm()
        else:
            form = RiderRegistrationForm()
            
        return render(request, self.template_name, {
            'form': form,
            'user_type': user_type
        })

    def post(self, request):
        user_type = request.POST.get('user_type', 'rider')  # Get from hidden field
        
        if user_type == 'driver':
            form = DriverRegistrationForm(request.POST)
        else:
            form = RiderRegistrationForm(request.POST)
        
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
                # Get license data from form
                license_number = form.cleaned_data.get('license_number', 'PENDING')
                license_image_url = form.cleaned_data.get('license_image_url', '')
                
                Driver.objects.create(
                    user=user,
                    license_number=license_number,
                    license_image_url=license_image_url,
                    license_expiry=date.today(),  # Placeholder - should be updated later
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


class driver_dashboard(View):
    template_name = 'TrikeGo_app/driver_dashboard.html'

    def get(self, request):
        if request.user.is_authenticated and request.user.trikego_user == 'D':
            # Get driver profile information
            try:
                driver_profile = Driver.objects.get(user=request.user)
                context = {
                    'user': request.user,
                    'driver_profile': driver_profile
                }
            except Driver.DoesNotExist:
                context = {
                    'user': request.user,
                    'driver_profile': None
                }
            return render(request, self.template_name, context)
        else:
            return redirect('user:landing')


class rider_dashboard(View):
    template_name = 'TrikeGo_app/rider_dashboard.html'

    def get(self, request):
        if request.user.is_authenticated and request.user.trikego_user == 'R':
            # Get rider profile information
            try:
                rider_profile = Rider.objects.get(user=request.user)
                context = {
                    'user': request.user,
                    'rider_profile': rider_profile
                }
            except Rider.DoesNotExist:
                context = {
                    'user': request.user,
                    'rider_profile': None
                }
            return render(request, self.template_name, context)
        else:
            return redirect('user:landing')


class admin_dashboard(View):
    template_name = 'TrikeGo_app/admin_dashboard.html'

    def get(self, request):
        if request.user.is_authenticated and request.user.trikego_user == 'A':
            # Get admin profile information
            try:
                admin_profile = Admin.objects.get(user=request.user)
                context = {
                    'user': request.user,
                    'admin_profile': admin_profile
                }
            except Admin.DoesNotExist:
                context = {
                    'user': request.user,
                    'admin_profile': None
                }
            return render(request, self.template_name, context)
        else:
            return redirect('user:landing')