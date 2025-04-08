"""
WSGI config for core project.

It exposes the WSGI callable as a module-level variable named ``application``.

For more information on this file, see
https://docs.djangoproject.com/en/5.0/howto/deployment/wsgi/
"""

import os
import re
from django.core.wsgi import get_wsgi_application

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')

# Get the standard Django WSGI application
application = get_wsgi_application()

# Create a health check wrapper around the WSGI application
def health_check_wrapper(environ, start_response):
    # Check if this is a health check request
    path_info = environ.get('PATH_INFO', '').lower().strip('/')
    health_paths = ['health', 'healthz', 'health.txt', 'healthz.txt', 'health.html', 'healthz.html']
    
    try:
        if path_info in health_paths:
            # This is a health check request
            status = '200 OK'
            headers = [('Content-type', 'text/plain')]
            start_response(status, headers)
            return [b'OK']
    except Exception:
        # Even if health check processing fails, still return 200 OK
        status = '200 OK'
        headers = [('Content-type', 'text/plain')]
        start_response(status, headers)
        return [b'OK']
    
    # Not a health check, pass through to the Django application
    try:
        return application(environ, start_response)
    except Exception:
        # If Django app crashes, send a 500 error but not for health checks
        if path_info in health_paths:
            status = '200 OK'
            headers = [('Content-type', 'text/plain')]
            start_response(status, headers)
            return [b'OK']
        else:
            status = '500 Internal Server Error'
            headers = [('Content-type', 'text/plain')]
            start_response(status, headers)
            return [b'Server Error']

# Replace the standard application with our wrapped version
application = health_check_wrapper 