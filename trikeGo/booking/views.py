from django.shortcuts import render

# Create your views here.
from django.views import View

class MyBookings(View):
    template_name = 'booking/booking.html'

    def get(self, request):
        return render(request, self.template_name)
    
class BookView(View):
    template_name = 'booking/booking.html'

    def get(self, request):
        return render(request, self.template_name)
    
class CancelBooking(View):
    template_name = 'booking/booking.html'

    def get(self, request, booking_id):
        return render(request, self.template_name) 
