from django.urls import path
from django.views.generic import TemplateView
from django.http import HttpResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods

@csrf_exempt
@require_http_methods(["GET"])
def index(request):
    """Simple index page that confirms the app is running"""
    return HttpResponse("Telegram Bot Service is running", content_type="text/plain")

urlpatterns = [
    path('', index, name='index'),  # Root URL returns a simple status message
] 