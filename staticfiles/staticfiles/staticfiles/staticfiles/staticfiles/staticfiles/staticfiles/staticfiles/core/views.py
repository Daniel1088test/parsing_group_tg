import os
import logging
import shutil
import mimetypes
from django.conf import settings
from django.http import FileResponse, HttpResponse
from django.views.decorators.http import require_GET

logger = logging.getLogger('media_handler')

# Add a direct file serve function for the root index.html
def serve_root_index(request):
    """Serve index.html directly from the root directory for Railway deployment"""
    try:
        # First, look for index.html in the root directory
        index_path = os.path.join(settings.BASE_DIR, 'index.html')
        if os.path.exists(index_path):
            logger.info(f"Serving root index.html from: {index_path}")
            return FileResponse(open(index_path, 'rb'), content_type='text/html')
        
        # If not found, try templates/admin_panel/index.html
        admin_index_path = os.path.join(settings.BASE_DIR, 'templates', 'admin_panel', 'index.html')
        if os.path.exists(admin_index_path):
            logger.info(f"Serving admin panel index.html from: {admin_index_path}")
            return FileResponse(open(admin_index_path, 'rb'), content_type='text/html')
        
        # If none found, fallback to the railway_index_view
        logger.warning("No index.html found, falling back to railway_index_view")
        return railway_index_view(request)
    except Exception as e:
        logger.error(f"Error serving root index.html: {e}")
        return railway_index_view(request)

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

# Wrapper view for index to handle Railway environment
def railway_index_view(request):
    """Special index view for Railway deployment"""
    try:
        # First try the normal index view from admin_panel
        from admin_panel.views import index_view
        return index_view(request)
    except Exception as e:
        import logging
        logger = logging.getLogger('railway')
        logger.error(f"Error in index view: {e}")
        
        # Fallback to a more styled response using our base.html template
        from django.shortcuts import render
        
        # Try to render the template directly
        try:
            return render(request, 'admin_panel/index.html', {
                'MEDIA_URL': '/media/',
                'messages': [],
                'categories': [],
                'sessions': [],
            })
        except Exception as template_error:
            logger.error(f"Error rendering index template: {template_error}")
            
            # Try to render base template
            try:
                return render(request, 'base.html', {
                    'title': 'Telegram Parser',
                    'content': 'The Telegram bot is running. Please log in to access the admin panel.'
                })
            except Exception as base_error:
                logger.error(f"Error rendering base template: {base_error}")
            
            # Ultimate fallback - render a styled HTML page
            from django.http import HttpResponse
            html = '''
            <!DOCTYPE html>
            <html>
            <head>
                <title>Telegram Channel Parser</title>
                <meta charset="UTF-8">
                <meta name="viewport" content="width=device-width, initial-scale=1.0">
                <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.2/dist/css/bootstrap.min.css" rel="stylesheet">
                <style>
                    body { padding: 20px; background-color: #f8f9fc; font-family: 'Nunito', sans-serif; }
                    .container { max-width: 1200px; margin: 0 auto; }
                    .card { border-radius: 8px; box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1); margin-top: 20px; }
                    .card-header { background-color: #4e73df; color: white; font-weight: bold; }
                    .btn-primary { background-color: #4e73df; border-color: #4e73df; }
                    .btn-primary:hover { background-color: #2e59d9; border-color: #2653d4; }
                </style>
            </head>
            <body>
                <div class="container">
                    <div class="row">
                        <div class="col-md-8 offset-md-2">
                            <h1 class="text-primary mt-5">Telegram Channel Parser</h1>
                            <div class="card">
                                <div class="card-header">
                                    Status
                                </div>
                                <div class="card-body">
                                    <p class="card-text">The Telegram bot is running successfully. Please log in to access the dashboard.</p>
                                    <div class="d-grid gap-2">
                                        <a href="/admin_panel/" class="btn btn-primary">Go to Admin Panel</a>
                                        <a href="/login/" class="btn btn-secondary">Login</a>
                                    </div>
                                </div>
                            </div>
                        </div>
                    </div>
                </div>
                <script src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.2/dist/js/bootstrap.bundle.min.js"></script>
            </body>
            </html>
            '''
            return HttpResponse(html, content_type='text/html')