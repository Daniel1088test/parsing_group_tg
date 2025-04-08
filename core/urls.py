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
from django.http import HttpResponse, FileResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_GET
import os
import logging
from PIL import Image, ImageDraw
from django.views.static import serve

logger = logging.getLogger('media_handler')

# Простий health check endpoint
@csrf_exempt
@require_GET
def health_check(request):
    """Simple health check endpoint that always returns OK"""
    return HttpResponse("OK", content_type="text/plain")

# Custom media handler to handle missing files
@require_GET
def serve_media(request, path):
    """
    Custom media file handler that creates missing files on demand
    """
    file_path = os.path.join(settings.MEDIA_ROOT, path)
    
    # Check if file exists
    if os.path.exists(file_path):
        return FileResponse(open(file_path, 'rb'))
    
    # File doesn't exist - create placeholder
    logger.warning(f"Media file not found: {file_path}")
    
    # Create placeholder directories as needed
    placeholder_dir = os.path.join(settings.STATIC_ROOT, 'img')
    os.makedirs(placeholder_dir, exist_ok=True)
    os.makedirs(os.path.dirname(file_path), exist_ok=True)
    
    # Determine placeholder type based on file extension
    # Default placeholder paths
    image_placeholder = os.path.join(placeholder_dir, 'placeholder-image.png')
    video_placeholder = os.path.join(placeholder_dir, 'placeholder-video.png')
    
    # Create placeholders if they don't exist
    try:
        if not os.path.exists(image_placeholder):
            # Create image placeholder
            img = Image.new('RGB', (300, 200), color=(240, 240, 240))
            draw = ImageDraw.Draw(img)
            draw.rectangle([(0, 0), (299, 199)], outline=(200, 200, 200), width=2)
            draw.text((150, 100), "IMAGE", fill=(100, 100, 100))
            img.save(image_placeholder)
            logger.info(f"Created placeholder image: {image_placeholder}")
            
        if not os.path.exists(video_placeholder):
            # Create video placeholder
            img = Image.new('RGB', (300, 200), color=(240, 240, 240))
            draw = ImageDraw.Draw(img)
            draw.rectangle([(0, 0), (299, 199)], outline=(200, 200, 200), width=2)
            draw.text((150, 100), "VIDEO", fill=(100, 100, 100))
            img.save(video_placeholder)
            logger.info(f"Created placeholder video: {video_placeholder}")
    except Exception as e:
        logger.error(f"Error creating placeholders: {e}")
    
    # Choose the appropriate placeholder based on file extension
    if path.lower().endswith(('.jpg', '.jpeg', '.png', '.gif')):
        placeholder = image_placeholder
    elif path.lower().endswith(('.mp4', '.avi', '.mov', '.webm')):
        placeholder = video_placeholder
    else:
        placeholder = image_placeholder
    
    try:
        # Copy the placeholder to the requested location
        import shutil
        shutil.copy2(placeholder, file_path)
        logger.info(f"Created placeholder for missing file: {path}")
        return FileResponse(open(file_path, 'rb'))
    except Exception as e:
        logger.error(f"Error copying placeholder: {e}")
    
    # If all else fails, return 404
    return HttpResponse("Media not found", status=404)

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
    
    # Custom media handler
    path('media/<path:path>', serve_media, name='serve_media'),
]

# Serve media and static files
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
else:
    # Even in production, we need to serve media files
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)