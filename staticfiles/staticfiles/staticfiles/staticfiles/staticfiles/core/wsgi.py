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
from django.core.wsgi import get_wsgi_application

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
    application = get_wsgi_application()
    
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
    
    # Override the root URL handler with a direct approach
    _original_application = application

    def application(environ, start_response):
        """WSGI application with direct handling for root URL"""
        path_info = environ.get('PATH_INFO', '')
        
        # Directly serve the root URL with full index.html template
        if path_info == '/' or path_info == '':
            start_response('200 OK', [('Content-Type', 'text/html; charset=utf-8')])
            
            # Load the original template content for direct serving without Django
            try:
                with open(os.path.join(os.path.dirname(os.path.dirname(__file__)), 'templates', 'admin_panel', 'index.html'), 'rb') as f:
                    template_content = f.read()
                    return [template_content]
            except:
                # Fallback to direct HTML with all necessary elements
                return [b"""{% load custom_filters %}
{% load static %}
<!DOCTYPE html>
<html lang="uk">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Telegram Parser | Monitoring channels</title>    

    <!-- Bootstrap 5 CSS -->
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.2/dist/css/bootstrap.min.css" rel="stylesheet">
    <!-- DataTables CSS -->
    <link rel="stylesheet" href="https://cdn.datatables.net/1.13.6/css/dataTables.bootstrap5.min.css">
    <link rel="stylesheet" href="https://cdn.datatables.net/responsive/2.5.0/css/responsive.bootstrap5.min.css">
    <!-- Font Awesome -->
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.2/css/all.min.css">
    <style>
        :root {
            --primary-color: #4e73df;
            --secondary-color: #8e54e9;
        }
        body {
            background-color: #f8f9fc;
            font-family: 'Nunito', sans-serif;
        }
        .navbar {
            background: linear-gradient(to right, var(--primary-color), var(--secondary-color));
            box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
        }
        .card {
            border: none;
            border-radius: 0.5rem;
            box-shadow: 0 0.15rem 1.75rem 0 rgba(58, 59, 69, 0.1);
            margin-bottom: 1.5rem;
        }
        .card-header {
            background: linear-gradient(to right, var(--primary-color), var(--secondary-color));
            color: white;
            font-weight: 600;
            padding: 1rem 1.25rem;
        }
    </style>
</head>
<body>
    <!-- Navigation -->
    <nav class="navbar navbar-expand-lg navbar-dark">
        <div class="container">
            <a class="navbar-brand" href="/">
                <i class="fas fa-robot me-2"></i>
                Telegram Parser
            </a>
            <button class="navbar-toggler" type="button" data-bs-toggle="collapse" data-bs-target="#navbarNav">
                <span class="navbar-toggler-icon"></span>
            </button>
            <div class="collapse navbar-collapse" id="navbarNav">
                <ul class="navbar-nav ms-auto">
                    <li class="nav-item">
                        <a class="nav-link" href="#messages"><i class="fas fa-comments me-1"></i> Messages</a>
                    </li>
                    <li class="nav-item">
                        <a class="nav-link" href="/admin_panel/"><i class="fas fa-sign-in-alt me-1"></i> Admin panel</a>
                    </li>
                </ul>
            </div>
        </div>
    </nav>

    <!-- Hero Section -->
    <section class="py-5 bg-gradient-primary text-white" style="background: linear-gradient(135deg, #4e73df 0%, #8e54e9 100%);">
        <div class="container text-center py-5">
            <h1 class="display-4 fw-bold mb-4">Telegram Parser</h1>
            <p class="lead mb-5">
                The fastest and most convenient service for monitoring messages from telegram channels.
                Get up-to-date information in real time.
            </p>
            <a href="#messages" class="btn btn-light btn-lg">
                <i class="fas fa-search me-2"></i> View messages
            </a>
            <a href="https://t.me/chan_parsing_mon_bot" class="btn btn-info btn-lg ms-2">
                <i class="fab fa-telegram me-2"></i> Open Telegram Bot
            </a>
        </div>
    </section>

    <!-- Main Content -->
    <section class="py-5" id="messages">
        <div class="container">
            <h2 class="text-center mb-5">Latest Messages</h2>
            <div class="row">
                <div class="col-md-12 text-center">
                    <div class="card shadow mb-4">
                        <div class="card-body">
                            <p class="lead">Please go to the admin panel to view and manage messages.</p>
                            <a href="/admin_panel/" class="btn btn-primary btn-lg mt-3">
                                <i class="fas fa-sign-in-alt me-2"></i> Go to Admin Panel
                            </a>
                        </div>
                    </div>
                </div>
            </div>
        </div>
    </section>

    <!-- Footer -->
    <footer class="bg-dark text-white py-4 mt-5">
        <div class="container">
            <div class="text-center">
                <p class="mb-0">&copy; 2025 Telegram Parser. All rights reserved.</p>
            </div>
        </div>
    </footer>

    <!-- jQuery -->
    <script src="https://code.jquery.com/jquery-3.7.1.min.js"></script>
    <!-- Bootstrap JS -->
    <script src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.2/dist/js/bootstrap.bundle.min.js"></script>
</body>
</html>"""]
        
        # For all other URLs, use the original Django application
        return _original_application(environ, start_response)
        
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
# Restart trigger: 2025-04-09 14:11:36

# Restart trigger: 1323719b28a62cd7# Restart trigger: 09.04.2025 14:35:06,90 

# Restart trigger: 2025-04-09 11:53:18.011476+00:00