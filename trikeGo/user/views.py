# In trikeGo/user/views.py

from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login
from django.contrib import messages
from django.views import View
from .forms import DriverRegistrationForm, RiderRegistrationForm, LoginForm, DriverVerificationForm
from .models import Driver, Rider, CustomUser
from booking.forms import BookingForm # Import the booking form
from datetime import date

class LandingPage(View):
    template_name = 'TrikeGo_app/landingPage.html'
    def get(self, request):
        form = LoginForm()
        return render(request, self.template_name, {'form': form})

class Login(View):
    template_name = 'TrikeGo_app/landingPage.html'

    def post(self, request):
        form = LoginForm(request, data=request.POST)
        if form.is_valid():
            username = form.cleaned_data.get('username')
            password = form.cleaned_data.get('password')
            user = authenticate(username=username, password=password)
            if user is not None:
                login(request, user)
                # --- CORRECTED HERE ---
                if user.trikego_user == 'D':
                    return redirect('user:driver_dashboard')
                # --- AND HERE ---
                elif user.trikego_user == 'R':
                    return redirect('user:rider_dashboard')
                # --- AND HERE ---
                elif user.trikego_user == 'A':
                    return redirect('user:admin_dashboard')
                return redirect('user:logged_in')

        messages.error(request, "Invalid username or password.")
        return redirect('/#login')

    def get(self, request):
        return redirect('user:landing')

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
        # --- CORRECTED HERE ---
        if not request.user.is_authenticated or request.user.trikego_user != 'D':
            return redirect('user:landing')
        profile = Driver.objects.filter(user=request.user).first()
        return render(request, self.template_name, {'user': request.user, 'driver_profile': profile})

class RiderDashboard(View):
    template_name = 'TrikeGo_app/rider_dashboard.html'
    def get(self, request):
        # --- THIS IS WHERE YOUR ERROR OCCURRED, NOW CORRECTED ---
        if not request.user.is_authenticated or request.user.trikego_user != 'R':
            return redirect('user:landing')

        profile = Rider.objects.filter(user=request.user).first()
        booking_form = BookingForm()
        context = {
            'user': request.user,
            'rider_profile': profile,
            'booking_form': booking_form
        }
        return render(request, self.template_name, context)

class AdminDashboard(View):
    template_name = 'TrikeGo_app/admin_dashboard.html'

    def get(self, request):
        # --- CORRECTED HERE ---
        if not request.user.is_authenticated or getattr(request.user, 'trikego_user', None) != 'A':
            return redirect('user:landing')

        context = {
            "drivers": Driver.objects.select_related("user").all(),
            "riders": Rider.objects.select_related("user").all(),
            "users": CustomUser.objects.all(),
            "verification_form": DriverVerificationForm(),
        }
        return render(request, self.template_name, context)

    def post(self, request):
        # --- CORRECTED HERE ---
        if not request.user.is_authenticated or getattr(request.user, 'trikego_user', None) != 'A':
            return redirect('user:landing')

        form = DriverVerificationForm(request.POST)

        if form.is_valid():
            driver_id = form.cleaned_data['driver_id']
            driver = Driver.objects.get(id=driver_id)
            driver.is_verified = not driver.is_verified
            driver.save(update_fields=["is_verified"])
            messages.success(request, f"Driver {driver.user.username}'s verification status has been updated.")
        else:
            for field, errors in form.errors.items():
                for error in errors:
                    messages.error(request, f"{field}: {error}")

        return redirect('user:admin_dashboard')