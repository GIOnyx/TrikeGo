from django.shortcuts import render

def landing_page(request):
    return render(request, "TrikeGo_app/landingPage.html")

def login_page(request):
    return render(request, "TrikeGo_app/login.html")

def register_page(request):
    return render(request, "TrikeGo_app/register.html")
