from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login
from django.contrib import messages
from django.views import View
from .forms import DriverRegistrationForm, RiderRegistrationForm
from .models import Driver, Rider, CustomUser
from datetime import date


class LandingPage(View):
    template_name = 'TrikeGo_app/landingPage.html'
    def get(self, request):
        return render(request, self.template_name)


class Login(View):
    template_name = 'TrikeGo_app/login.html'

    def get(self, request):
        return render(request, self.template_name)
    
    def post(self, request):
        username = request.POST.get("username")
        password = request.POST.get("password")
        user = authenticate(request, username=username, password=password)

        if user:
            login(request, user)
            if user.trikego_user == 'D':
                return redirect('user:driver_dashboard')
            elif user.trikego_user == 'R':
                return redirect('user:rider_dashboard')
            elif user.trikego_user == 'A':
                return redirect('user:admin_dashboard')
            return redirect('user:logged_in')
        
        messages.error(request, "Invalid username or password")
        return render(request, self.template_name)


class RegisterPage(View):
    template_name = 'TrikeGo_app/register.html'

    def get(self, request):
        user_type = request.GET.get('type', 'rider')
        form = DriverRegistrationForm() if user_type == 'driver' else RiderRegistrationForm()
        return render(request, self.template_name, {'form': form, 'user_type': user_type})

    def post(self, request):
        user_type = request.POST.get('user_type', 'rider')
        form = DriverRegistrationForm(request.POST) if user_type == 'driver' else RiderRegistrationForm(request.POST)
        
        if form.is_valid():
            user = form.save(commit=False)
            user.trikego_user = 'D' if user_type == 'driver' else 'R'
            user.save()

            if user_type == 'driver':
                Driver.objects.create(
                    user=user,
                    license_number=form.cleaned_data.get('license_number', 'PENDING'),
                    license_image_url=form.cleaned_data.get('license_image_url', ''),
                    license_expiry=date.today(),
                    date_hired=date.today(),
                    years_of_service=0
                )
            else:
                Rider.objects.create(user=user)

            messages.success(request, f"{user_type.capitalize()} registration successful! Please log in.")
            return redirect('user:landing')
        
        return render(request, self.template_name, {'form': form, 'user_type': user_type})


class LoggedIn(View):
    template_name = 'TrikeGo_app/tempLoggedIn.html'
    def get(self, request):
        return render(request, self.template_name) if request.user.is_authenticated else redirect('user:landing')


class DriverDashboard(View):
    template_name = 'TrikeGo_app/driver_dashboard.html'
    def get(self, request):
        if not request.user.is_authenticated or request.user.trikego_user != 'D':
            return redirect('user:landing')
        profile = Driver.objects.filter(user=request.user).first()
        return render(request, self.template_name, {'user': request.user, 'driver_profile': profile})


class RiderDashboard(View):
    template_name = 'TrikeGo_app/rider_dashboard.html'
    def get(self, request):
        if not request.user.is_authenticated or request.user.trikego_user != 'R':
            return redirect('user:landing')
        profile = Rider.objects.filter(user=request.user).first()
        return render(request, self.template_name, {'user': request.user, 'rider_profile': profile})


class AdminDashboard(View):
    template_name = 'TrikeGo_app/admin_dashboard.html'
    def get(self, request):
        if not request.user.is_authenticated or getattr(request.user, 'trikego_user', None) != 'A':
            return redirect('user:landing')

        return render(request, self.template_name, {
            "drivers": Driver.objects.select_related("user").all(),
            "riders": Rider.objects.select_related("user").all(),
            "all_drivers": CustomUser.objects.filter(trikego_user="D"),
            "all_riders": CustomUser.objects.filter(trikego_user="R"),
        })
