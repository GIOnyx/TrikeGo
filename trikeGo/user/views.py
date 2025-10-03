from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login
from django.contrib import messages
from django.views import View
from .forms import CustomerForm
from .models import Driver, Rider
from datetime import date

# Create your views here.
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
        user_type = request.GET.get('type', 'rider')
        return render(request, self.template_name,{'form': form, 'user_type': user_type})

    def post(self, request):
        form = CustomerForm(request.POST)
        user_type = request.POST.get('user_type', 'rider')
        if form.is_valid():
            user = form.save()
            if user_type == 'driver':
                license_number = request.POST.get('license_number')
                license_image_url = request.POST.get('license_image_url')
                if not license_number:
                    messages.error(request, "Driver’s license number is required for driver registration.")
                    return render(request, self.template_name, {'form': form, 'user_type': user_type})
                Driver.objects.create(
                    user=user,
                    license_number=license_number,
                    license_expiry=date.today(),
                    date_hired=date.today(),
                    years_of_service=0,
                    is_available=True,
                    license_image_url=license_image_url
                )
            else:
                Rider.objects.create(user=user)
            return redirect('user:landing')
        return render(request, self.template_name, {'form': form, 'user_type': user_type})
    
class logged_in(View):
    template_name = 'TrikeGo_app/tempLoggedIn.html'

    def get(self, request):
        if request.user.is_authenticated:
            return render(request, self.template_name)
        else:
            return redirect('user:landing')
