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
from django.http import HttpResponse
import os
import socket

# Simple health check view for Railway
def health_check(request):
    return HttpResponse("OK", content_type="text/plain")

# Information view to check configuration - accessible to everyone for debugging
def info_view(request):
    public_host = os.getenv("PUBLIC_HOST", "Not set")
    web_host = os.getenv("WEB_SERVER_HOST", "Not set")
    web_port = os.getenv("WEB_SERVER_PORT", "Not set")
    allowed_hosts = settings.ALLOWED_HOSTS
    
    # Get local hostname and IP
    hostname = socket.gethostname()
    try:
        local_ip = socket.gethostbyname(hostname)
    except:
        local_ip = "Could not determine local IP"
    
    # Get all environment variables (but filter sensitive ones)
    env_vars = {}
    for key, value in os.environ.items():
        if any(sensitive in key.lower() for sensitive in ['secret', 'password', 'token', 'key', 'hash']):
            env_vars[key] = "******"
        else:
            env_vars[key] = value
    
    info = f"""
    <html>
    <head>
        <title>Site Configuration</title>
        <style>
            body {{ font-family: Arial, sans-serif; margin: 20px; }}
            h1, h2 {{ color: #333; }}
            .info {{ background: #f5f5f5; padding: 15px; border-radius: 5px; margin-bottom: 20px; }}
            .key {{ font-weight: bold; }}
            .env-list {{ max-height: 300px; overflow-y: auto; }}
        </style>
    </head>
    <body>
        <h1>Site Configuration</h1>
        <div class="info">
            <h2>Server Information</h2>
            <p><span class="key">Hostname:</span> {hostname}</p>
            <p><span class="key">Local IP:</span> {local_ip}</p>
            <p><span class="key">PUBLIC_HOST:</span> {public_host}</p>
            <p><span class="key">WEB_SERVER_HOST:</span> {web_host}</p>
            <p><span class="key">WEB_SERVER_PORT:</span> {web_port}</p>
            <p><span class="key">ALLOWED_HOSTS:</span> {', '.join(allowed_hosts)}</p>
            <p><span class="key">Current URL:</span> {request.build_absolute_uri()}</p>
            <p><span class="key">Debug Mode:</span> {settings.DEBUG}</p>
        </div>
        
        <div class="info">
            <h2>Environment Variables</h2>
            <div class="env-list">
                <ul>
                    {' '.join(f'<li><span class="key">{k}:</span> {v}</li>' for k, v in sorted(env_vars.items()))}
                </ul>
            </div>
        </div>
        
        <div class="info">
            <h2>Quick Links</h2>
            <p><a href="/">Homepage</a></p>
            <p><a href="/admin/">Admin Panel</a></p>
            <p><a href="/health/">Health Check</a></p>
        </div>
    </body>
    </html>
    """
    return HttpResponse(info)

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', include('admin_panel.urls')),
    # Add health check endpoint
    path('health/', health_check, name='health_check'),
    # Add info view
    path('info/', info_view, name='info_view'),
]

# Add static and media files routing
if settings.DEBUG:
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
else:
    # In production, still serve media files through Django
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)