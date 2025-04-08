import os
import logging
from django.conf import settings
from django.http import FileResponse
import re
import shutil
import mimetypes

logger = logging.getLogger('middleware')

class MediaFilesMiddleware:
    """Middleware to handle missing media files and create placeholders on demand"""
    
    def __init__(self, get_response):
        self.get_response = get_response
        
        # One-time configuration during initialization
        # Ensure placeholder directories exist
        self._create_directories()
        
        # Create placeholder images if they don't exist
        self.create_placeholders()
        
    def _create_directories(self):
        """Create necessary directories with proper permissions"""
        dirs_to_create = [
            os.path.join(settings.STATIC_ROOT, 'img'),
            os.path.join(settings.MEDIA_ROOT, 'messages'),
            'data/sessions'
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
            image_placeholder = os.path.join(settings.STATIC_ROOT, 'img', 'placeholder-image.png')
            video_placeholder = os.path.join(settings.STATIC_ROOT, 'img', 'placeholder-video.png')
            
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
                    # If PIL is not available, create an empty file
                    with open(image_placeholder, 'wb') as f:
                        f.write(b'')
                    logger.warning(f"Created empty placeholder file: {image_placeholder} (PIL not available)")
                    
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
                    # If PIL is not available, create an empty file
                    with open(video_placeholder, 'wb') as f:
                        f.write(b'')
                    logger.warning(f"Created empty placeholder file: {video_placeholder} (PIL not available)")
        except Exception as e:
            logger.error(f"Error creating placeholders: {e}")
    
    def __call__(self, request):
        # Run the view first without creating directories to avoid unnecessary operations
        response = self.get_response(request)
        
        # Post-processing if the response is a 404 for a media file
        if response.status_code == 404:
            # Check if this is a media file request
            media_path_match = re.match(r'^/messages/(.+\.(jpg|jpeg|png|gif|mp4|avi|mov|webm))$', request.path)
            if media_path_match:
                try:
                    file_name = media_path_match.group(1)
                    logger.warning(f"Attempted to access missing media file: {file_name}")
                    
                    # Define placeholder paths
                    image_placeholder = os.path.join(settings.STATIC_ROOT, 'img', 'placeholder-image.png')
                    video_placeholder = os.path.join(settings.STATIC_ROOT, 'img', 'placeholder-video.png')
                    
                    # Determine which placeholder to use based on file extension
                    file_ext = os.path.splitext(file_name)[1].lower()
                    if file_ext in ['.jpg', '.jpeg', '.png', '.gif']:
                        placeholder = image_placeholder
                    else:
                        placeholder = video_placeholder
                    
                    # Create the media directory if needed
                    target_path = os.path.join(settings.MEDIA_ROOT, 'messages', file_name)
                    target_dir = os.path.dirname(target_path)
                    
                    # Only create directory if it doesn't exist
                    if not os.path.exists(target_dir):
                        os.makedirs(target_dir, exist_ok=True)
                    
                    # Copy the placeholder to the requested location
                    if os.path.exists(placeholder):
                        # Create the file with correct MIME type
                        content_type, encoding = mimetypes.guess_type(target_path)
                        if not content_type:
                            if file_ext in ['.jpg', '.jpeg', '.png', '.gif']:
                                content_type = f"image/{file_ext[1:]}"
                            elif file_ext in ['.mp4', '.avi', '.mov', '.webm']:
                                content_type = f"video/{file_ext[1:]}"
                            else:
                                content_type = "application/octet-stream"
                        
                        # Copy the file
                        shutil.copy2(placeholder, target_path)
                        
                        # Set file permissions
                        os.chmod(target_path, 0o644)
                        
                        logger.info(f"Created placeholder for missing file: {file_name}")
                        
                        # Return the created file with correct content type
                        response = FileResponse(open(target_path, 'rb'))
                        response['Content-Type'] = content_type
                        return response
                        
                except Exception as e:
                    logger.error(f"Error creating placeholder for {request.path}: {e}")
                
        return response 