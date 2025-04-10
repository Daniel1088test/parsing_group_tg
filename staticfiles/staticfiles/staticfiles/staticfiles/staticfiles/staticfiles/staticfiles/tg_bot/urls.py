"""URL patterns for the tg_bot app."""
from django.urls import path
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt

@csrf_exempt
def api_root(request):
    """API root endpoint"""
    return JsonResponse({
        'status': 'ok',
        'name': 'Telegram Parser API',
        'version': '1.0'
    })

@csrf_exempt
def api_channels(request):
    """Return a list of channels (simplified version that always works)"""
    # This is a simple version that doesn't depend on the database
    return JsonResponse({
        'status': 'ok',
        'channels': []  # Empty list as fallback
    })

def bot_status(request):
    """Return status information about the bot."""
    return JsonResponse({
        'status': 'online',
        'version': '1.0.0',
        'name': 'Telegram Parser Bot',
    })

def webhook_info(request):
    """Return webhook information."""
    return JsonResponse({
        'webhook_url': None,
        'active': True,
        'health': 'OK'
    })

urlpatterns = [
    path('', api_root, name='api_root'),
    path('channels/', api_channels, name='api_channels'),
    path('status/', bot_status, name='bot_status'),
    path('webhook/info/', webhook_info, name='webhook_info'),
] 