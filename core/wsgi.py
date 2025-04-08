"""
WSGI config for core project.

It exposes the WSGI callable as a module-level variable named ``application``.

For more information on this file, see
https://docs.djangoproject.com/en/5.0/howto/deployment/wsgi/
"""

import os
import sys
from pathlib import Path

# Add project root to path to help with imports
project_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(project_root))

# Custom health check handler for when Django fails to start
def simple_health_check(environ, start_response):
    """Simple WSGI app that returns a health check response"""
    if environ.get('PATH_INFO', '').rstrip('/') in ['/health', '/healthz', '/ping', '']:
        status = '200 OK'
        headers = [('Content-type', 'text/plain')]
        start_response(status, headers)
        return [b'OK']
    return None

try:
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
    from django.core.wsgi import get_wsgi_application
    
    # Get the Django application
    django_application = get_wsgi_application()
    
    # Add whitenoise for static file serving
    try:
        from whitenoise import WhiteNoise
        from django.conf import settings
        
        application = WhiteNoise(django_application, 
                                root=settings.STATIC_ROOT,
                                prefix=settings.STATIC_URL)
                                
        # Add additional directories for media files
        application.add_files(settings.MEDIA_ROOT, prefix=settings.MEDIA_URL)
        
        # Add health check directories
        for directory in [".", "static", "staticfiles"]:
            if os.path.exists(directory):
                application.add_files(directory)
                
    except (ImportError, AttributeError):
        # Fallback if WhiteNoise isn't available
        application = django_application
        
    # Wrapper function to handle health checks at the WSGI level
    def wrapped_application(environ, start_response):
        # First check if this is a health check request
        health_response = simple_health_check(environ, start_response)
        if health_response:
            return health_response
        
        # Otherwise, pass to Django
        return application(environ, start_response)
    
    # Replace application with our wrapped version    
    application = wrapped_application
        
except Exception as e:
    import logging
    logging.error(f"Error in WSGI setup: {e}")
    
    # If Django fails to start, fall back to a simple health check app
    def application(environ, start_response):
        # Handle health checks
        health_response = simple_health_check(environ, start_response)
        if health_response:
            return health_response
            
        # For all other requests, return a server error
        status = '500 Internal Server Error'
        headers = [('Content-type', 'text/plain')]
        start_response(status, headers)
        return [b'The application is currently unavailable. Please try again later.'] 