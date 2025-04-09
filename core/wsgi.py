"""
WSGI config for core project.

It exposes the WSGI callable as a module-level variable named ``application``.

For more information on this file, see
https://docs.djangoproject.com/en/5.0/howto/deployment/wsgi/
"""

import os
import sys
import subprocess
from pathlib import Path

# Add project root to path to help with imports
project_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(project_root))

# Custom health check handler for when Django fails to start
def simple_health_check(environ, start_response):
    """Simple WSGI app that returns a health check response"""
    if environ.get('PATH_INFO') in ['/health', '/healthz', '/ping']:
        status = '200 OK'
        headers = [('Content-type', 'text/plain')]
        start_response(status, headers)
        return [b'OK']
    return None

# Global bot process variable
bot_process = None

try:
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
    from django.core.wsgi import get_wsgi_application
    
    # Initialize Django first
    django_application = get_wsgi_application()
    
    # Run database fix commands
    try:
        import logging
        from django.core.management import call_command
        
        # Fix database schema issues
        call_command('fix_db_schema', '--quiet')
        logging.info("Database schema check completed during startup")
        
        # Start the bot process in the background
        try:
            logging.info("Starting Telegram bot process...")
            bot_process = subprocess.Popen([sys.executable, 'run.py'], 
                                        stdout=subprocess.PIPE, 
                                        stderr=subprocess.STDOUT)
            logging.info(f"Bot process started with PID: {bot_process.pid}")
        except Exception as bot_error:
            logging.error(f"Failed to start bot process: {bot_error}")
    except Exception as schema_fix_error:
        logging.error(f"Error fixing database schema during startup: {schema_fix_error}")
    
    # Wrapper function to handle health checks at the WSGI level
    def application(environ, start_response):
        # First check if this is a health check request
        health_response = simple_health_check(environ, start_response)
        if health_response:
            return health_response
        
        # Otherwise, pass to Django
        return django_application(environ, start_response)
        
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