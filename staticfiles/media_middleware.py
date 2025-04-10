import os
import logging
from pathlib import Path
from django.conf import settings
from django.http import HttpResponse, FileResponse, HttpResponseNotFound
from django.core.files.storage import default_storage

logger = logging.getLogger('media_middleware')

class MediaRedirectMiddleware:
    """
    Middleware that intercepts requests for media files and handles them directly.
    This helps with deployment environments like Railway where media file handling may be problematic.
    """
    
    def __init__(self, get_response):
        self.get_response = get_response
        # Setup paths
        self.media_url = getattr(settings, 'MEDIA_URL', '/media/').rstrip('/') + '/'
        self.media_root = getattr(settings, 'MEDIA_ROOT', 'media')
        self.static_root = getattr(settings, 'STATIC_ROOT', 'staticfiles')
        
        # Ensure placeholder images exist
        self.placeholder_image = os.path.join(self.static_root, 'img', 'placeholder-image.png')
        self.placeholder_video = os.path.join(self.static_root, 'img', 'placeholder-video.png')
        
        # Create directories and placeholders if needed
        self._ensure_directories()
        self._ensure_placeholders()
        
        logger.info(f"MediaRedirectMiddleware initialized (MEDIA_ROOT: {self.media_root})")
    
    def _ensure_directories(self):
        """Ensure required directories exist"""
        dirs = [
            self.media_root,
            os.path.join(self.media_root, 'messages'),
            os.path.join(self.static_root, 'img'),
            os.path.join(self.static_root, 'media')
        ]
        
        for directory in dirs:
            if not os.path.exists(directory):
                try:
                    os.makedirs(directory, exist_ok=True)
                    logger.info(f"Created directory: {directory}")
                except Exception as e:
                    logger.error(f"Error creating directory {directory}: {e}")
    
    def _ensure_placeholders(self):
        """Ensure placeholder images exist"""
        placeholders = [
            (self.placeholder_image, 'image'),
            (self.placeholder_video, 'video')
        ]
        
        for path, placeholder_type in placeholders:
            if not os.path.exists(path):
                try:
                    # Simple transparent 1x1 pixel PNG
                    with open(path, 'wb') as f:
                        f.write(b'\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x06\x00\x00\x00\x1f\x15\xc4\x89\x00\x00\x00\nIDATx\x9cc\x00\x01\x00\x00\x05\x00\x01\r\n-\xb4\x00\x00\x00\x00IEND\xaeB`\x82')
                    logger.info(f"Created placeholder {placeholder_type}: {path}")
                except Exception as e:
                    logger.error(f"Error creating placeholder {placeholder_type}: {e}")
    
    def __call__(self, request):
        # Check if the request is for a media file
        if request.path.startswith(self.media_url):
            # Extract the relative path
            rel_path = request.path[len(self.media_url):]
            
            # Determine file type from extension
            file_ext = os.path.splitext(rel_path)[1].lower()
            is_image = file_ext in ['.jpg', '.jpeg', '.png', '.gif', '.webp', '.svg']
            is_video = file_ext in ['.mp4', '.webm', '.ogg', '.mov']
            
            # Full path to the requested file
            full_path = os.path.join(self.media_root, rel_path)
            
            # Check if file exists
            if os.path.exists(full_path) and os.path.isfile(full_path):
                try:
                    # Serve the file directly
                    return FileResponse(open(full_path, 'rb'))
                except Exception as e:
                    logger.error(f"Error serving media file {full_path}: {e}")
                    # Fall through to placeholder logic
            
            # Handle missing files with placeholders
            logger.warning(f"Media file not found: {full_path}")
            
            # Return appropriate placeholder
            try:
                placeholder = self.placeholder_video if is_video else self.placeholder_image
                if os.path.exists(placeholder):
                    return FileResponse(open(placeholder, 'rb'))
                else:
                    logger.error(f"Placeholder not found: {placeholder}")
                    return HttpResponseNotFound("Media file not found")
            except Exception as e:
                logger.error(f"Error serving placeholder: {e}")
                return HttpResponseNotFound("Media file not found")
        
        # For non-media requests, just pass through
        return self.get_response(request)