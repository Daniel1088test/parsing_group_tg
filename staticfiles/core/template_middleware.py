"""
Middleware to ensure templates are properly loaded in Railway environment
"""
import os
import logging
from django.conf import settings
from django.http import HttpResponse

logger = logging.getLogger('template_middleware')

class TemplateDebugMiddleware:
    """
    Middleware to log template rendering information and provide fallbacks
    """
    
    def __init__(self, get_response):
        self.get_response = get_response
        
        # Log template directories for debugging
        if hasattr(settings, 'TEMPLATES'):
            for template_engine in settings.TEMPLATES:
                if 'DIRS' in template_engine:
                    for directory in template_engine['DIRS']:
                        logger.info(f"Template directory: {directory}")
                        if os.path.exists(directory):
                            files = os.listdir(directory)
                            logger.info(f"Files in {directory}: {files}")
                        else:
                            logger.warning(f"Template directory does not exist: {directory}")
        
        # Log static files configuration
        logger.info(f"STATIC_URL: {settings.STATIC_URL}")
        logger.info(f"STATIC_ROOT: {settings.STATIC_ROOT}")
        logger.info(f"STATICFILES_DIRS: {settings.STATICFILES_DIRS}")
        
        # Log media files configuration
        logger.info(f"MEDIA_URL: {settings.MEDIA_URL}")
        logger.info(f"MEDIA_ROOT: {settings.MEDIA_ROOT}")
    
    def __call__(self, request):
        # Log request information
        logger.debug(f"Received request for: {request.path}")
        
        # Process request with regular middleware chain
        response = self.get_response(request)
        
        # If this is the root URL and we got a very simple response,
        # it might be the plain text issue. Let's check and provide a better response.
        if request.path == '/' and response.status_code == 200:
            content_type = response.get('Content-Type', '')
            content = getattr(response, 'content', b'').decode('utf-8', errors='ignore')
            
            if 'text/plain' in content_type and 'Telegram bot is running' in content:
                logger.warning("Detected plain text 'Telegram bot is running' response for root URL, upgrading to HTML")
                
                # Replace with better HTML response
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
        
        return response 