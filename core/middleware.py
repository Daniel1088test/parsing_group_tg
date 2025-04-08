import os
import logging
from django.conf import settings
from django.http import FileResponse, HttpResponseNotFound
import re
import shutil
import mimetypes
from pathlib import Path

logger = logging.getLogger('middleware')

class MediaFilesMiddleware:
    """Middleware to handle missing media files and create placeholders on demand"""
    
    def __init__(self, get_response):
        self.get_response = get_response
        
        # One-time configuration during initialization
        # Setup paths
        self.media_url = getattr(settings, 'MEDIA_URL', '/media/').rstrip('/') + '/'
        self.media_root = getattr(settings, 'MEDIA_ROOT', 'media')
        self.static_root = getattr(settings, 'STATIC_ROOT', 'staticfiles')
        
        # Ensure placeholder directories exist
        self._create_directories()
        
        # Create placeholder images if they don't exist
        self.create_placeholders()
        
        logger.info(f"MediaFilesMiddleware initialized (MEDIA_ROOT: {self.media_root})")
        
    def _create_directories(self):
        """Create necessary directories with proper permissions"""
        dirs_to_create = [
            os.path.join(self.static_root, 'img'),
            os.path.join(self.media_root, 'messages'),
            'data/sessions',
            os.path.join(self.static_root, 'media')
        ]
        
        for directory in dirs_to_create:
            try:
                # Check if directory exists before trying to create it
                if not os.path.exists(directory):
                    os.makedirs(directory, exist_ok=True)
                    logger.info(f"Created directory: {directory}")
                
                # Set directory permissions to 0755
                try:
                    os.chmod(directory, 0o755)
                except Exception as e:
                    logger.warning(f"Could not set permissions on directory {directory}: {e}")
            except Exception as e:
                # Only log as error if it's not a "File exists" error
                if "File exists" not in str(e):
                    logger.error(f"Error creating directory {directory}: {e}")
                else:
                    # Log as info instead of error for "File exists"
                    logger.debug(f"Directory already exists: {directory}")
        
    def create_placeholders(self):
        """Create placeholder images if they don't exist"""
        try:
            # Define placeholder paths
            image_placeholder = os.path.join(self.static_root, 'img', 'placeholder-image.png')
            video_placeholder = os.path.join(self.static_root, 'img', 'placeholder-video.png')
            
            # Copy placeholders to media directory for direct access
            media_image = os.path.join(self.static_root, 'media', 'placeholder-image.png')
            media_video = os.path.join(self.static_root, 'media', 'placeholder-video.png')
            
            # Create image placeholder
            if not os.path.exists(image_placeholder):
                try:
                    from PIL import Image, ImageDraw
                    img = Image.new('RGB', (300, 200), color=(240, 240, 240))
                    draw = ImageDraw.Draw(img)
                    draw.rectangle([(0, 0), (299, 199)], outline=(200, 200, 200), width=2)
                    draw.text((150, 100), "IMAGE", fill=(100, 100, 100))
                    img.save(image_placeholder)
                    logger.info(f"Created placeholder image: {image_placeholder}")
                    
                    # Set file permissions
                    os.chmod(image_placeholder, 0o644)
                except ImportError:
                    # If PIL is not available, create a simple 1x1 transparent PNG
                    with open(image_placeholder, 'wb') as f:
                        f.write(b'\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x06\x00\x00\x00\x1f\x15\xc4\x89\x00\x00\x00\nIDATx\x9cc\x00\x01\x00\x00\x05\x00\x01\r\n-\xb4\x00\x00\x00\x00IEND\xaeB`\x82')
                    logger.warning(f"Created basic placeholder: {image_placeholder} (PIL not available)")
                    
            # Create video placeholder
            if not os.path.exists(video_placeholder):
                try:
                    from PIL import Image, ImageDraw
                    img = Image.new('RGB', (300, 200), color=(240, 240, 240))
                    draw = ImageDraw.Draw(img)
                    draw.rectangle([(0, 0), (299, 199)], outline=(200, 200, 200), width=2)
                    draw.text((150, 100), "VIDEO", fill=(100, 100, 100))
                    img.save(video_placeholder)
                    logger.info(f"Created placeholder video: {video_placeholder}")
                    
                    # Set file permissions
                    os.chmod(video_placeholder, 0o644)
                except ImportError:
                    # If PIL is not available, create a simple 1x1 transparent PNG
                    with open(video_placeholder, 'wb') as f:
                        f.write(b'\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x06\x00\x00\x00\x1f\x15\xc4\x89\x00\x00\x00\nIDATx\x9cc\x00\x01\x00\x00\x05\x00\x01\r\n-\xb4\x00\x00\x00\x00IEND\xaeB`\x82')
                    logger.warning(f"Created basic placeholder: {video_placeholder} (PIL not available)")
                    
            # Copy placeholder to media directory for direct access
            for src, dest in [(image_placeholder, media_image), (video_placeholder, media_video)]:
                if os.path.exists(src) and not os.path.exists(dest):
                    shutil.copy2(src, dest)
                    logger.info(f"Copied placeholder to media directory: {dest}")
                    try:
                        os.chmod(dest, 0o644)
                    except Exception as e:
                        logger.warning(f"Could not set permissions on placeholder copy {dest}: {e}")
                        
        except Exception as e:
            logger.error(f"Error creating placeholders: {e}")
    
    def __call__(self, request):
        # Check if this is a media file request before running the main view
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
                placeholder = os.path.join(self.static_root, 'img', 'placeholder-video.png' if is_video else 'placeholder-image.png')
                if os.path.exists(placeholder):
                    response = FileResponse(open(placeholder, 'rb'))
                    # Set appropriate content type for the placeholder
                    response['Content-Type'] = 'image/png'
                    return response
                else:
                    logger.error(f"Placeholder not found: {placeholder}")
                    return HttpResponseNotFound("Media file not found")
            except Exception as e:
                logger.error(f"Error serving placeholder: {e}")
                return HttpResponseNotFound("Media file not found")

        # For non-media requests or if we didn't handle the media, pass to the next middleware
        response = self.get_response(request)
        
        # Post-processing for 404 responses that might be media files
        if response.status_code == 404:
            # Check if this is a media-like path that wasn't caught earlier (could be server-side routing issues)
            media_path_match = re.match(r'^/(?:media/)?(.+\.(jpg|jpeg|png|gif|mp4|avi|mov|webm))$', request.path)
            if media_path_match:
                try:
                    file_name = media_path_match.group(1)
                    logger.warning(f"404 for possible media file: {file_name}")
                    
                    # Define placeholder paths
                    file_ext = os.path.splitext(file_name)[1].lower()
                    is_video = file_ext in ['.mp4', '.webm', '.ogg', '.mov', '.avi']
                    
                    placeholder = os.path.join(self.static_root, 'img', 'placeholder-video.png' if is_video else 'placeholder-image.png')
                    
                    # Try to use the placeholder
                    if os.path.exists(placeholder):
                        response = FileResponse(open(placeholder, 'rb'))
                        response['Content-Type'] = 'image/png'
                        response['X-Media-Placeholder'] = 'true'
                        return response
                        
                except Exception as e:
                    logger.error(f"Error creating placeholder for {request.path}: {e}")
                
        return response 