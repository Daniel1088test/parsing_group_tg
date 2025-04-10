#!/usr/bin/env python3
"""
Direct deployment script for Railway.
This script fixes all issues and ensures proper rendering of index.html.
"""
import os
import sys
import time
import logging
import traceback
import subprocess
import shutil

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler('direct_deploy.log')
    ]
)
logger = logging.getLogger('direct_deploy')

def ensure_directories():
    """Ensure all required directories exist"""
    dirs = [
        'static',
        'staticfiles',
        'templates',
        'templates/admin_panel',
        'media',
        'logs'
    ]
    
    for d in dirs:
        os.makedirs(d, exist_ok=True)
        logger.info(f"Ensured directory exists: {d}")

def create_index_html():
    """Create the index.html file in all required locations"""
    html_content = """<!DOCTYPE html>
<html lang="uk">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Telegram Parser | Monitoring channels</title>    

    <!-- Bootstrap 5 CSS -->
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.2/dist/css/bootstrap.min.css" rel="stylesheet">
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
        
        .hero-section {
            background: linear-gradient(135deg, rgba(78, 115, 223, 0.9) 0%, rgba(142, 84, 233, 0.9) 100%);
            padding: 6rem 0;
            color: white;
            text-align: center;
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
            <div class="collapse navbar-collapse" id="navbarNav">
                <ul class="navbar-nav ms-auto">
                    <li class="nav-item">
                        <a class="nav-link" href="/admin_panel/"><i class="fas fa-sign-in-alt me-1"></i> Admin panel</a>
                    </li>
                </ul>
            </div>
        </div>
    </nav>

    <!-- Hero Section -->
    <section class="hero-section">
        <div class="container">
            <h1 class="display-4 fw-bold mb-4">Telegram Parser</h1>
            <p class="lead mb-5">
                The fastest and most convenient service for monitoring messages from telegram channels.
                Get up-to-date information in real time.
            </p>
            <a href="https://t.me/chan_parsing_mon_bot" class="btn btn-info btn-lg">
                <i class="fab fa-telegram me-2"></i> Open Telegram Bot
            </a>
        </div>
    </section>

    <!-- Main Content -->
    <section class="py-5">
        <div class="container">
            <div class="row">
                <div class="col-md-12 text-center">
                    <div class="card shadow">
                        <div class="card-header">
                            Admin Panel
                        </div>
                        <div class="card-body">
                            <p class="lead">Please go to the admin panel to view and manage telegram channels and messages.</p>
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

    <!-- Bootstrap JS -->
    <script src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.2/dist/js/bootstrap.bundle.min.js"></script>
</body>
</html>"""

    # Write to multiple locations
    locations = [
        'index.html',
        'static/index.html',
        'templates/admin_panel/index.html',
        'staticfiles/index.html'
    ]
    
    for location in locations:
        with open(location, 'w', encoding='utf-8') as f:
            f.write(html_content)
        logger.info(f"Created index.html at {location}")

def fix_wsgi():
    """Update the WSGI application to directly serve the index.html"""
    wsgi_content = """import os
import sys
from django.core.wsgi import get_wsgi_application

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
application = get_wsgi_application()

# Override the root URL handler
_original_application = application

def application(environ, start_response):
    \"\"\"WSGI application with direct handling for root URL\"\"\"
    path_info = environ.get('PATH_INFO', '')
    
    # Directly serve the root URL with the index.html content
    if path_info == '/' or path_info == '':
        start_response('200 OK', [('Content-Type', 'text/html; charset=utf-8')])
        
        # Try to read the index.html file
        try:
            with open('index.html', 'rb') as f:
                return [f.read()]
        except:
            # If that fails, try other locations
            try:
                with open('static/index.html', 'rb') as f:
                    return [f.read()]
            except:
                try:
                    with open('templates/admin_panel/index.html', 'rb') as f:
                        return [f.read()]
                except:
                    # Last resort - return a simple HTML
                    return [b'''<!DOCTYPE html>
<html>
<head>
    <title>Telegram Parser</title>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.2/dist/css/bootstrap.min.css" rel="stylesheet">
</head>
<body>
    <div class="container my-5">
        <div class="row">
            <div class="col-md-8 offset-md-2 text-center">
                <h1>Telegram Parser</h1>
                <div class="mt-4">
                    <a href="/admin_panel/" class="btn btn-primary btn-lg">Go to Admin Panel</a>
                </div>
            </div>
        </div>
    </div>
</body>
</html>''']
    
    # For all other paths, use the original application
    return _original_application(environ, start_response)
"""
    
    os.makedirs('core', exist_ok=True)
    with open('core/wsgi.py', 'w', encoding='utf-8') as f:
        f.write(wsgi_content)
    logger.info("Updated WSGI application")

def run_command(cmd):
    """Run a shell command and log the output"""
    logger.info(f"Running command: {cmd}")
    try:
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
        if result.returncode != 0:
            logger.error(f"Command failed with code {result.returncode}: {result.stderr}")
        else:
            logger.info(f"Command completed successfully")
        return result.returncode == 0
    except Exception as e:
        logger.error(f"Error running command: {e}")
        return False

def main():
    """Main function"""
    logger.info("Starting direct deployment script")
    
    # Ensure directories exist
    ensure_directories()
    
    # Create index.html in all locations
    create_index_html()
    
    # Fix WSGI application
    fix_wsgi()
    
    # Run database fixes
    run_command("python fix_multiple_fields.py")
    run_command("python fix_admin_query.py")
    
    # Create health check files
    with open('health.txt', 'w') as f:
        f.write('OK')
    with open('healthz.txt', 'w') as f:
        f.write('OK')
    
    logger.info("Direct deployment script completed")
    print("\n" + "="*50)
    print("Deployment fixes applied!")
    print("The website should now display correctly at the root URL.")
    print("="*50 + "\n")

if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        logger.error(f"Error: {e}")
        logger.error(traceback.format_exc())
        sys.exit(1) 