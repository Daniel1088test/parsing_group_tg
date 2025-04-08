"""
Health check middleware for Django to ensure that health check endpoints 
always return 200 OK, regardless of the state of the application.
"""

import logging
import sys
from django.http import HttpResponse

logger = logging.getLogger(__name__)

class HealthCheckMiddleware:
    """
    Django middleware that intercepts health check requests 
    to ensure they always return 200 OK.
    """
    
    def __init__(self, get_response):
        self.get_response = get_response
    
    def __call__(self, request):
        # Check if this is a health check request
        path = request.path.lower().strip('/')
        
        health_paths = [
            'health', 
            'healthz', 
            'health.txt', 
            'healthz.txt',
            'health.html', 
            'healthz.html'
        ]
        
        if path in health_paths:
            try:
                logger.info(f"Health check request detected: {path} from {request.META.get('REMOTE_ADDR')}")
                
                # Додаємо інформацію про здоров'я у відповідь, якщо запит приймає JSON
                if 'application/json' in request.META.get('HTTP_ACCEPT', ''):
                    import json
                    import django
                    health_data = {
                        'status': 'ok',
                        'version': django.__version__,
                        'python': sys.version,
                        'timestamp': str(django.utils.timezone.now())
                    }
                    return HttpResponse(json.dumps(health_data), content_type="application/json")
                    
                # Default plain text response
                return HttpResponse("OK", content_type="text/plain")
            except Exception as e:
                # Навіть якщо виникла помилка, ми все одно повертаємо 200 OK для health check
                logger.error(f"Error in health check middleware: {e}")
                return HttpResponse("OK", content_type="text/plain")
        
        # Not a health check, continue with normal request processing
        return self.get_response(request) 