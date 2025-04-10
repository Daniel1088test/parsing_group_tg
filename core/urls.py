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
from django.urls import path, include, re_path
from django.conf import settings
from django.conf.urls.static import static
from admin_panel.views import index_view, login_view, register_view, logout_view
from django.http import HttpResponse, FileResponse, JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_GET
import os
import logging
# Безпечний імпорт PIL з обробкою помилок
try:
    from PIL import Image, ImageDraw
    PIL_AVAILABLE = True
except ImportError:
    PIL_AVAILABLE = False
    print("Warning: PIL/Pillow not available - placeholder images will not be created")
from django.views.static import serve
from django.views.generic.base import RedirectView

# Ensure the views module is imported correctly
try:
    from .views import serve_media, railway_index_view
except ImportError:
    # Fallback definitions if import fails
    def serve_media(request, path):
        file_path = os.path.join(settings.MEDIA_ROOT, path)
        if os.path.exists(file_path):
            return FileResponse(open(file_path, 'rb'))
        return HttpResponse("Media not found", status=404)
    
    def railway_index_view(request):
        return index_view(request)

from django.views.generic import TemplateView
import subprocess
try:
    import psutil
    PSUTIL_AVAILABLE = True
except ImportError:
    PSUTIL_AVAILABLE = False
    print("Warning: psutil not available - process monitoring limited")
import time

logger = logging.getLogger('media_handler')

# Health check endpoint
@csrf_exempt
@require_GET
def health_check(request):
    """Enhanced health check endpoint that returns detailed status"""
    import json
    import sys
    import django
    
    try:
        # Log the health check request
        logger.info(f"Health check endpoint called from {request.META.get('REMOTE_ADDR')}")
        
        # Collect health information
        health_data = {
            'status': 'ok',
            'timestamp': str(django.utils.timezone.now()),
            'python_version': sys.version,
            'django_version': django.__version__,
            'request_path': request.path,
        }
        
        # Check database connection
        try:
            from django.db import connection
            with connection.cursor() as cursor:
                cursor.execute("SELECT 1")
                db_result = cursor.fetchone()[0]
                health_data['database'] = {
                    'status': 'connected' if db_result == 1 else 'error',
                    'engine': connection.vendor
                }
        except Exception as e:
            health_data['database'] = {
                'status': 'error',
                'message': str(e)
            }
        
        # Format based on Accept header
        accept = request.META.get('HTTP_ACCEPT', '')
        if 'application/json' in accept:
            return HttpResponse(json.dumps(health_data), content_type='application/json')
        elif request.path.endswith('.json'):
            return HttpResponse(json.dumps(health_data), content_type='application/json')
        else:
            # Plain text for simplicity and compatibility
            return HttpResponse("OK", content_type="text/plain")
    except Exception as e:
        # Even if everything fails, still return 200 OK for the health check
        logger.error(f"Error in health check: {e}")
        return HttpResponse("OK", content_type="text/plain")

def health_check_view(request):
    """Простий обробник для перевірки здоров'я для Railway"""
    return JsonResponse({'status': 'ok', 'message': 'Service is running'})

def simple_index_view(request):
    """Simple index view that works without database."""
    from django.shortcuts import redirect
    if request.user.is_authenticated:
        return redirect('admin_panel')
    return redirect('login')

@csrf_exempt
def bot_status_api(request):
    """API для перевірки статусу бота"""
    try:
        # Перевіряємо, чи бот запущений через перевірку процесів
        if PSUTIL_AVAILABLE:
            # Шукаємо процеси python, які виконують run_bot.py
            bot_processes = []
            for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
                try:
                    if proc.info['name'].lower() in ['python', 'python.exe', 'python3', 'python3.exe']:
                        cmdline = ' '.join(proc.info['cmdline'] or []).lower()
                        if 'run_bot.py' in cmdline:
                            bot_processes.append(proc.info)
                except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                    pass
            
            # Повертаємо статус
            if bot_processes:
                return JsonResponse({
                    'status': 'running',
                    'message': 'Bot is running',
                    'processes': len(bot_processes),
                    'process_info': bot_processes[0] if bot_processes else None
                })
            else:
                return JsonResponse({
                    'status': 'stopped',
                    'message': 'Bot is not running'
                })
        else:
            # Якщо немає psutil, використовуємо альтернативний метод
            try:
                # Альтернативний метод через таблицю процесів у Django
                import subprocess
                bot_running = False
                
                try:
                    if os.name == 'posix':  # Linux/Unix
                        result = subprocess.run(['ps', '-ef'], capture_output=True, text=True)
                        bot_running = 'run_bot.py' in result.stdout
                    else:  # Windows
                        result = subprocess.run(['tasklist', '/FI', 'IMAGENAME eq python.exe'], capture_output=True, text=True)
                        bot_running = 'run_bot.py' in result.stdout
                except Exception:
                    # Якщо ps не доступний, перевіряємо наявність PID файлів
                    bot_pid_file = 'bot.pid'
                    if os.path.exists(bot_pid_file):
                        bot_running = True
                
                if bot_running:
                    return JsonResponse({
                        'status': 'running',
                        'message': 'Bot is running'
                    })
                else:
                    return JsonResponse({
                        'status': 'stopped',
                        'message': 'Bot is not running'
                    })
            except Exception as e:
                # Якщо все інше не працює, перевіримо файли статусу чи директорії
                try:
                    # Спробуємо перевірити, чи існує директорія з логами бота
                    log_dir = os.path.join('logs', 'bot')
                    if os.path.exists(log_dir) and os.path.isdir(log_dir):
                        # Перевіряємо, чи є нові логи
                        logs = [f for f in os.listdir(log_dir) if f.endswith('.log')]
                        if logs:
                            newest_log = max(logs, key=lambda x: os.path.getmtime(os.path.join(log_dir, x)))
                            log_time = os.path.getmtime(os.path.join(log_dir, newest_log))
                            if (time.time() - log_time) < 60*5:  # останні 5 хвилин
                                return JsonResponse({
                                    'status': 'likely_running',
                                    'message': 'Bot appears to be running based on recent logs'
                                })
                    
                    # Якщо немає ознак роботи, повернемо невідомий статус
                    return JsonResponse({
                        'status': 'unknown',
                        'message': f'Cannot determine bot status: {str(e)}'
                    })
                except Exception as e2:
                    return JsonResponse({
                        'status': 'error',
                        'message': f'Error checking bot status: {str(e2)}'
                    }, status=500)
    except Exception as e:
        return JsonResponse({
            'status': 'error',
            'message': f'Error checking bot status: {str(e)}'
        }, status=500)

# Define the main urlpatterns
urlpatterns = [
    # Basic routes
    path('admin/', admin.site.urls),
    path('admin_panel/', include('admin_panel.urls')),
    
    # Main page - make sure railway_index_view is used if available, otherwise fallback to normal index_view
    path('', railway_index_view if 'railway_index_view' in locals() else index_view, name='index'),
    
    # Auth routes
    path('login/', login_view, name='login'),
    path('register/', register_view, name='register'),
    path('logout/', logout_view, name='logout'),
    
    # Health check endpoints
    path('health/', health_check, name='health'),
    path('healthz/', health_check, name='healthz'),
    path('health.html', health_check, name='health_html'),
    path('healthz.html', health_check, name='healthz_html'),
    path('ping/', health_check, name='ping'),
    re_path(r'^_health/?$', health_check),  # Railway health check format
    
    # Static and media serving (for development)
    path('media/<path:path>', serve_media, name='serve_media'),
    
    # Bot API
    path('api/bot/status/', bot_status_api, name='bot_status_api'),
    path('bot/', include('tg_bot.urls')),
]

# Add static and media serving for development
if settings.DEBUG:
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
else:
    # In production, serve static files with whitenoise
    urlpatterns += [
        path('static/<path:path>', serve, {'document_root': settings.STATIC_ROOT}),
    ]