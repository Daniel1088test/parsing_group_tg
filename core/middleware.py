import os
import logging
from django.conf import settings
from django.http import FileResponse
import re

logger = logging.getLogger('middleware')

class MediaFilesMiddleware:
    """Middleware to handle missing media files and create placeholders on demand"""
    
    def __init__(self, get_response):
        self.get_response = get_response
        
        # One-time configuration during initialization
        # Ensure placeholder directories exist
        os.makedirs(os.path.join(settings.STATIC_ROOT, 'img'), exist_ok=True)
        os.makedirs(os.path.join(settings.MEDIA_ROOT, 'messages'), exist_ok=True)
        
        # Create placeholder images if they don't exist
        self.create_placeholders()
        
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
                except ImportError:
                    # If PIL is not available, create an empty file
                    with open(video_placeholder, 'wb') as f:
                        f.write(b'')
                    logger.warning(f"Created empty placeholder file: {video_placeholder} (PIL not available)")
        except Exception as e:
            logger.error(f"Error creating placeholders: {e}")
    
    def __call__(self, request):
        # Run the view
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
                    
                    # Determine which placeholder to use
                    file_ext = os.path.splitext(file_name)[1].lower()
                    if file_ext in ['.jpg', '.jpeg', '.png', '.gif']:
                        placeholder = image_placeholder
                    else:
                        placeholder = video_placeholder
                    
                    # Create the media directory if needed
                    target_path = os.path.join(settings.MEDIA_ROOT, 'messages', file_name)
                    os.makedirs(os.path.dirname(target_path), exist_ok=True)
                    
                    # Copy the placeholder to the requested location
                    if os.path.exists(placeholder):
                        import shutil
                        shutil.copy2(placeholder, target_path)
                        logger.info(f"Created placeholder for missing file: {file_name}")
                        
                        # Return the copied file
                        return FileResponse(open(target_path, 'rb'))
                except Exception as e:
                    logger.error(f"Error creating placeholder for {request.path}: {e}")
                
        return response 