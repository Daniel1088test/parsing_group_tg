import os
import logging
import shutil
import mimetypes
from django.conf import settings
from django.http import FileResponse, HttpResponse
from django.views.decorators.http import require_GET

logger = logging.getLogger('media_handler')

@require_GET
def serve_media(request, path):
    """
    Custom media file handler that creates placeholders for missing files
    """
    # Determine file path
    if path.startswith('messages/'):
        file_path = os.path.join(settings.MEDIA_ROOT, path)
    else:
        file_path = os.path.join(settings.MEDIA_ROOT, 'messages', path)
    
    # Check if file exists
    if os.path.exists(file_path):
        # Return existing file
        content_type, encoding = mimetypes.guess_type(file_path)
        response = FileResponse(open(file_path, 'rb'))
        if content_type:
            response['Content-Type'] = content_type
        return response
    
    logger.warning(f"Media file not found: {file_path}")
    
    # Create necessary directories
    os.makedirs(os.path.dirname(file_path), exist_ok=True)
    
    # Create placeholder directories as needed
    placeholder_dir = os.path.join(settings.STATIC_ROOT, 'img')
    os.makedirs(placeholder_dir, exist_ok=True)
    
    # Determine which placeholder to use based on file extension
    file_ext = os.path.splitext(file_path)[1].lower()
    image_placeholder = os.path.join(placeholder_dir, 'placeholder-image.png')
    video_placeholder = os.path.join(placeholder_dir, 'placeholder-video.png')
    
    # Create placeholders if they don't exist
    if not os.path.exists(image_placeholder) or not os.path.exists(video_placeholder):
        try:
            from PIL import Image, ImageDraw
            
            # Create image placeholder
            if not os.path.exists(image_placeholder):
                img = Image.new('RGB', (300, 200), color=(240, 240, 240))
                draw = ImageDraw.Draw(img)
                draw.rectangle([(0, 0), (299, 199)], outline=(200, 200, 200), width=2)
                draw.text((150, 100), "IMAGE", fill=(100, 100, 100))
                img.save(image_placeholder)
                logger.info(f"Created placeholder image: {image_placeholder}")
                
            # Create video placeholder
            if not os.path.exists(video_placeholder):
                img = Image.new('RGB', (300, 200), color=(240, 240, 240))
                draw = ImageDraw.Draw(img)
                draw.rectangle([(0, 0), (299, 199)], outline=(200, 200, 200), width=2)
                draw.text((150, 100), "VIDEO", fill=(100, 100, 100))
                img.save(video_placeholder)
                logger.info(f"Created placeholder video: {video_placeholder}")
        except Exception as e:
            logger.error(f"Error creating placeholder images: {e}")
    
    # Determine content type and source placeholder
    content_type = None
    if file_ext in ['.jpg', '.jpeg', '.png', '.gif']:
        placeholder = image_placeholder
        content_type = f"image/{file_ext[1:]}"
    elif file_ext in ['.mp4', '.avi', '.mov', '.webm']:
        placeholder = video_placeholder
        content_type = f"video/{file_ext[1:]}"
    else:
        placeholder = image_placeholder
        content_type = "application/octet-stream"
    
    # Copy the placeholder to the requested location
    try:
        if os.path.exists(placeholder):
            shutil.copy2(placeholder, file_path)
            logger.info(f"Created placeholder for missing file: {path}")
            
            # Set file permissions
            try:
                os.chmod(file_path, 0o644)
            except Exception as e:
                logger.warning(f"Could not set permissions for {file_path}: {e}")
            
            # Return the file with appropriate content type
            response = FileResponse(open(file_path, 'rb'))
            if content_type:
                response['Content-Type'] = content_type
            return response
    except Exception as e:
        logger.error(f"Error creating placeholder for {path}: {e}")
    
    # If all else fails, return 404
    return HttpResponse(f"Media file not found: {path}", status=404)