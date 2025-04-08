"""
Health check middleware for Django application
Handles health check requests and ensures they always respond correctly,
even when other parts of the application might be having issues.
"""
import os
import logging
import shutil
from pathlib import Path
from django.http import HttpResponse

logger = logging.getLogger('middleware')

class HealthCheckMiddleware:
    """
    Middleware to handle health check requests in Django.
    This is crucial for Railway to know our service is alive.
    """
    
    def __init__(self, get_response):
        self.get_response = get_response
        
        # Create required health check static files
        self._create_static_health_files()
        
        # Create placeholder images for media
        self._ensure_media_files()
        
        logger.info("HealthCheckMiddleware initialized")
    
    def __call__(self, request):
        # Handle health check requests immediately
        path = request.path.lower().strip('/')
        
        if path in ['health', 'healthz', 'health.txt', 'healthz.txt', 'health.html', 'healthz.html', 'ping']:
            # Always respond OK to health checks
            logger.debug(f"Health check request: {path}")
            return HttpResponse("OK", content_type="text/plain")
        
        # For all other requests, proceed normally
        return self.get_response(request)
    
    def _create_static_health_files(self):
        """Create static health check files for web server direct access"""
        directories = [
            ".", "static", "staticfiles", "static/health", "staticfiles/health"
        ]
        
        # Create directories if they don't exist
        for directory in directories:
            os.makedirs(directory, exist_ok=True)
        
        # Create health check files in each directory
        for directory in directories:
            for filename in ["health.html", "healthz.html", "health.txt", "healthz.txt"]:
                file_path = os.path.join(directory, filename)
                try:
                    with open(file_path, "w") as f:
                        f.write("OK")
                    logger.debug(f"Created health check file: {file_path}")
                except Exception as e:
                    logger.error(f"Error creating health check file {file_path}: {e}")
    
    def _ensure_media_files(self):
        """
        Ensure media directories exist and contain placeholder files for missing media.
        This helps the app run correctly even if media files are missing.
        """
        try:
            # Create media directories
            media_dirs = ["media", "staticfiles/media", "media/messages", "staticfiles/media/messages"]
            for directory in media_dirs:
                os.makedirs(directory, exist_ok=True)
                logger.info(f"Created directory: {directory}")
            
            # Create/copy placeholder files
            placeholder_files = [
                ("staticfiles/media/placeholder-image.png", "media/placeholder-image.png"),
                ("staticfiles/media/placeholder-video.png", "media/placeholder-video.png"),
                ("staticfiles/media/messages/placeholder-image.png", "media/messages/placeholder-image.png"),
                ("staticfiles/media/messages/placeholder-video.png", "media/messages/placeholder-video.png"),
            ]
            
            # Try to find an existing placeholder to copy
            found_placeholder = False
            for src, dest in placeholder_files:
                # If source exists, copy it to other destinations
                if os.path.exists(src):
                    found_placeholder = True
                    for _, copy_dest in placeholder_files:
                        if src != copy_dest and not os.path.exists(copy_dest):
                            shutil.copy2(src, copy_dest)
                            logger.info(f"Copied placeholder to directory: {copy_dest}")
                    break
                # If destination exists, use it as source
                elif os.path.exists(dest):
                    found_placeholder = True
                    for copy_src, _ in placeholder_files:
                        if copy_src != dest and not os.path.exists(copy_src):
                            shutil.copy2(dest, copy_src)
                            logger.info(f"Copied placeholder to directory: {copy_src}")
                    break
            
            # If no placeholders were found, create them
            if not found_placeholder:
                try:
                    from PIL import Image, ImageDraw
                    
                    for src, _ in placeholder_files:
                        # Create a simple placeholder image
                        img = Image.new("RGB", (300, 200), color=(240, 240, 240))
                        draw = ImageDraw.Draw(img)
                        draw.rectangle([(0, 0), (299, 199)], outline=(200, 200, 200), width=2)
                        
                        # Add appropriate text based on file name
                        if "video" in src:
                            draw.text((150, 100), "VIDEO", fill=(100, 100, 100))
                        else:
                            draw.text((150, 100), "IMAGE", fill=(100, 100, 100))
                        
                        # Save the image
                        img.save(src)
                        logger.info(f"Created placeholder image: {src}")
                        
                        # Copy to other locations if needed
                        for _, dest_path in placeholder_files:
                            if not os.path.exists(dest_path):
                                shutil.copy2(src, dest_path)
                                logger.info(f"Copied placeholder to: {dest_path}")
                except Exception as e:
                    logger.error(f"Error creating placeholder images: {e}")
                    
            # Check for messages with media references and create placeholders if needed
            try:
                # Import here to avoid circular imports
                from django.conf import settings
                from admin_panel.models import Message
                
                messages_with_media = Message.objects.filter(media__isnull=False).exclude(media="")
                logger.info(f"Found {messages_with_media.count()} messages with media references")
                
                # Ensure each message's media file exists or replace with placeholder
                for message in messages_with_media:
                    if message.media:
                        media_path = os.path.join(settings.MEDIA_ROOT, str(message.media))
                        
                        if not os.path.exists(media_path):
                            # Create directory if needed
                            os.makedirs(os.path.dirname(media_path), exist_ok=True)
                            
                            # Copy appropriate placeholder based on media type
                            if message.media_type and "video" in message.media_type.lower():
                                placeholder = os.path.join(settings.MEDIA_ROOT, "placeholder-video.png")
                            else:
                                placeholder = os.path.join(settings.MEDIA_ROOT, "placeholder-image.png")
                                
                            # Make sure the placeholder exists
                            if not os.path.exists(placeholder):
                                # If not, use any available placeholder
                                for _, dest in placeholder_files:
                                    if os.path.exists(dest):
                                        placeholder = dest
                                        break
                            
                            # Create an empty file if no placeholder is available
                            if not os.path.exists(placeholder):
                                with open(media_path, "w") as f:
                                    f.write("PLACEHOLDER")
                                logger.info(f"Created empty placeholder for {media_path}")
                            else:
                                # Copy the placeholder
                                shutil.copy2(placeholder, media_path)
                                logger.info(f"Created placeholder for {media_path}")
            except Exception as e:
                logger.error(f"Error creating placeholders for message media: {e}")
                
        except Exception as e:
            logger.error(f"Error in _ensure_media_files: {e}")

class MediaFilesMiddleware:
    """
    Middleware to ensure media files exist.
    If media files are referenced in the database but don't exist on disk,
    this middleware creates placeholders to prevent errors.
    """
    
    def __init__(self, get_response):
        self.get_response = get_response
        
        # Create/check required media directories
        try:
            from django.conf import settings
            
            self.media_root = settings.MEDIA_ROOT
            os.makedirs(self.media_root, exist_ok=True)
            os.makedirs(os.path.join(self.media_root, "messages"), exist_ok=True)
            
            logger.info(f"MediaFilesMiddleware initialized (MEDIA_ROOT: {self.media_root})")
        except Exception as e:
            logger.error(f"Error initializing MediaFilesMiddleware: {e}")
    
    def __call__(self, request):
        # Just pass through to the next middleware/view
        return self.get_response(request)