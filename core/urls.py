"""
URL configuration for core project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.0/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from django.http import HttpResponse, JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_GET
from django.views.decorators.cache import never_cache
from django.shortcuts import redirect

@never_cache
@csrf_exempt
@require_GET
def health_check(request):
    """Simple health check endpoint that always returns OK"""
    return HttpResponse("OK", content_type="text/plain", status=200)

# Another simple health check route that always returns OK for Railway
def railway_health(request):
    """Simplified health check for Railway"""
    return HttpResponse("OK")

# Simple home page that doesn't depend on database
def simple_home(request):
    """Simple static homepage that always works"""
    html = """
    <!DOCTYPE html>
    <html>
    <head>
        <title>Telegram Channel Parser</title>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <style>
            body { font-family: Arial, sans-serif; line-height: 1.6; padding: 20px; max-width: 800px; margin: 0 auto; }
            a { display: inline-block; margin: 10px 0; padding: 10px 15px; background: #0088cc; color: white; text-decoration: none; border-radius: 4px; }
            h1 { color: #0088cc; }
        </style>
    </head>
    <body>
        <h1>Telegram Channel Parser</h1>
        <p>The application is running. Use one of the following options:</p>
        <div>
            <a href="/admin/">Go to Admin Panel</a>
        </div>
        <div>
            <a href="https://t.me/Channels_hunt_bot" target="_blank">Open Telegram Bot</a>
        </div>
        <div>
            <a href="/api/">API Endpoints</a>
        </div>
        <div>
            <a href="/health/">Health Check</a>
        </div>
    </body>
    </html>
    """
    return HttpResponse(html)

# API status endpoint that doesn't depend on database
@csrf_exempt
def api_status(request):
    """API status endpoint for health monitoring"""
    return JsonResponse({
        'status': 'ok',
        'version': '1.0',
        'environment': 'production' if not settings.DEBUG else 'development'
    })

urlpatterns = [
    path('admin/', admin.site.urls),
    path('health/', health_check, name='health_check'),  # Health check endpoint
    path('healthz/', railway_health, name='railway_health'),  # Alternative health check
    path('', simple_home, name='home'),  # Root shows simple static home
    path('api/', include('tg_bot.urls')),  # API endpoints
    path('api/status/', api_status, name='api_status'),  # API status endpoint
]

# Serve media files in development and production
urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

# Serve static files in development only (in production, we use whitenoise)
if settings.DEBUG:
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)