from django.shortcuts import render, redirect
from django.views import View
from .forms import CustomerForm
from .models import User

# Create your views here.
class Login(View):
    template_name = 'templates/login.html'

    def get(self, request):
        return render(request, self.template_name)

    def post(self, request):
        uname = request.POST.get('txtUname')
        pwd = request.POST.get('txtPwd')
        errorMessage = ''

        try:
            user = User.objects.get(username=uname)
            if pwd == user.password:
                request.session['username'] = user.username
                request.session['type'] = user.trikego_user
                print(request.session.get('type'))
                return redirect('user:loggedin')
            else:
                errorMessage = 'Invalid credentials.'
        except Exception:
            errorMessage = uname + ' does not exists.'

        return render(request, self.template_name, {'error': errorMessage})


class LoggedIn(View):
    template_name = 'templates/landingPage.html'

    def get(self, request):
        if (request.session.get('username')):
            return render(request, self.template_name)
        else:
            return redirect('user:login')
