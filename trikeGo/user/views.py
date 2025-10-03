from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login
from django.contrib import messages
from django.views import View
from .forms import CustomerForm
from .models import Rider, Driver
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