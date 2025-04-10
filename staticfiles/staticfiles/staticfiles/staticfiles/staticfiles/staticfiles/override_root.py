#!/usr/bin/env python3
"""
Script to forcibly override the root URL behavior to show a proper page.
"""
import os
import sys
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler('override_root.log')
    ]
)
logger = logging.getLogger('override_root')

def create_direct_index_html():
    """Create an index.html file in the static directory"""
    try:
        # Ensure directories exist
        os.makedirs('static', exist_ok=True)
        
        # Create index.html directly in static folder
        with open('static/index.html', 'w') as f:
            f.write('''<!DOCTYPE html>
<html>
<head>
    <title>Telegram Channel Parser</title>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.2/dist/css/bootstrap.min.css" rel="stylesheet">
    <style>
        body { padding: 20px; }
        .card { margin-top: 20px; }
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
                        <p class="card-text">Bot is running. Please go to the admin panel to manage channels.</p>
                        <a href="/admin_panel/" class="btn btn-primary">Go to Admin Panel</a>
                    </div>
                </div>
            </div>
        </div>
    </div>
    <script src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.2/dist/js/bootstrap.bundle.min.js"></script>
</body>
</html>''')
        
        # Also create in templates/admin_panel
        os.makedirs('templates/admin_panel', exist_ok=True)
        with open('templates/admin_panel/index.html', 'w') as f:
            f.write('''{% load static %}
<!DOCTYPE html>
<html>
<head>
    <title>Telegram Channel Parser</title>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.2/dist/css/bootstrap.min.css" rel="stylesheet">
    <style>
        body { padding: 20px; }
        .card { margin-top: 20px; }
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
                        <p class="card-text">Bot is running. Please go to the admin panel to manage channels.</p>
                        <a href="/admin_panel/" class="btn btn-primary">Go to Admin Panel</a>
                    </div>
                </div>
            </div>
        </div>
    </div>
    <script src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.2/dist/js/bootstrap.bundle.min.js"></script>
</body>
</html>''')
            
        logger.info("Created index.html files")
        return True
    except Exception as e:
        logger.error(f"Error creating index.html: {e}")
        return False

def create_direct_wsgi_app():
    """Create a direct WSGI application override"""
    try:
        # Create wsgi.py with an override for the root URL
        wsgi_content = '''import os
import sys
from django.core.wsgi import get_wsgi_application

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
application = get_wsgi_application()

# Override the root URL handler for Railway
_original_application = application

def application(environ, start_response):
    """WSGI application with special handling for root URL"""
    path_info = environ.get('PATH_INFO', '')
    
    # Directly serve the root URL with a proper page
    if path_info == '/' or path_info == '':
        start_response('200 OK', [('Content-Type', 'text/html')])
        return [b"""<!DOCTYPE html>
<html>
<head>
    <title>Telegram Channel Parser</title>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.2/dist/css/bootstrap.min.css" rel="stylesheet">
    <style>
        body { padding: 20px; }
        .card { margin-top: 20px; }
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
                        <p class="card-text">Bot is running. Please go to the admin panel to manage channels.</p>
                        <a href="/admin_panel/" class="btn btn-primary">Go to Admin Panel</a>
                    </div>
                </div>
            </div>
        </div>
    </div>
    <script src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.2/dist/js/bootstrap.bundle.min.js"></script>
</body>
</html>"""]
    
    # For all other URLs, use the original Django application
    return _original_application(environ, start_response)
'''
        
        with open('core/wsgi.py', 'w') as f:
            f.write(wsgi_content)
            
        logger.info("Created WSGI override")
        return True
    except Exception as e:
        logger.error(f"Error creating WSGI override: {e}")
        return False

def main():
    """Main function"""
    logger.info("Starting root URL override")
    
    create_direct_index_html()
    create_direct_wsgi_app()
    
    logger.info("Root URL override completed")
    
    print("\n" + "="*50)
    print("Root URL override applied!")
    print("The website should now display the proper page at the root URL.")
    print("="*50 + "\n")
    
    return True

if __name__ == "__main__":
    main() 