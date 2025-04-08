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
from admin_panel.views import index_view
from django.http import HttpResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_GET

# Простий health check endpoint
@csrf_exempt
@require_GET
def health_check(request):
    """Simple health check endpoint that always returns OK"""
    return HttpResponse("OK", content_type="text/plain")

# Перевизначаємо порядок URL-патернів - спочатку наш основний index_view, потім інші патерни
urlpatterns = [
    # Додаємо всі можливі шляхи для health check
    path('health', health_check),  # Без слешу
    path('health/', health_check, name='health'),  # Зі слешем
    path('healthz', health_check),  # Альтернативний - без слешу
    path('healthz/', health_check, name='healthz'),  # Альтернативний - зі слешем
    path('health.html', health_check),  # Варіант з розширенням
    
    # Основні URL-шляхи
    path('', index_view, name='index'),          # Головна сторінка - index.html з admin_panel
    path('admin/', admin.site.urls),             # Django admin
    path('admin_panel/', include('admin_panel.urls')),  # Включаємо решту URL з admin_panel
]

# Serve media and static files
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
else:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)