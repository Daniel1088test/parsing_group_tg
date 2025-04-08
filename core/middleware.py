import os
import logging
from django.conf import settings
from django.http import HttpResponse, FileResponse
from pathlib import Path

logger = logging.getLogger('middleware')

class MediaFilesMiddleware:
    """
    Middleware to ensure media files exist.
    Acts as a compatibility layer for code that might reference this middleware.
    The actual implementation is now in health_middleware.py.
    """
    
    def __init__(self, get_response):
        self.get_response = get_response
        logger.info("MediaFilesMiddleware (compatibility) initialized")
    
    def __call__(self, request):
        # Just pass through to the next middleware/view
        return self.get_response(request)

def serve_media(request, path):
    """
    Serve media files with fallbacks.
    This function serves as a fallback for serving media files.
    """
    # First try the normal file
    media_path = os.path.join(settings.MEDIA_ROOT, path)
    if os.path.exists(media_path) and os.path.isfile(media_path):
        return FileResponse(open(media_path, 'rb'))
        
    # Try the placeholder for images
    image_placeholder = os.path.join(settings.MEDIA_ROOT, 'placeholder-image.png')
    if os.path.exists(image_placeholder):
        return FileResponse(open(image_placeholder, 'rb'))
    
    # Generic fallback
    return HttpResponse("Media not found", status=404) 