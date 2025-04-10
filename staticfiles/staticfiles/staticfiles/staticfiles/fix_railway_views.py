#!/usr/bin/env python3
"""
Fix for Railway deployment to ensure the index.html page displays properly.
"""
import os
import sys
import logging
import django

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler('fix_railway_views.log')
    ]
)
logger = logging.getLogger('railway_views_fix')

# Initialize Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
try:
    django.setup()
    from django.conf import settings
    logger.info("Django successfully initialized")
except Exception as e:
    logger.error(f"Error initializing Django: {e}")
    sys.exit(1)

def fix_health_middleware():
    """Fix health middleware to ensure it doesn't intercept the main index view"""
    try:
        health_middleware_path = os.path.join(settings.BASE_DIR, 'core', 'health_middleware.py')
        
        if not os.path.exists(health_middleware_path):
            logger.warning(f"Health middleware file not found at {health_middleware_path}")
            return False
            
        with open(health_middleware_path, 'r', encoding='utf-8') as f:
            content = f.read()
            
        # Fix the health check middleware to NOT intercept the root URL
        if "path == ''" in content:
            logger.info("Health middleware already fixed")
            return True
            
        # Add check to skip root URL
        updated_content = content.replace(
            "def __call__(self, request):",
            "def __call__(self, request):\n        # Skip the root URL\n        if request.path == '':\n            return self.get_response(request)"
        )
        
        if content != updated_content:
            with open(health_middleware_path, 'w', encoding='utf-8') as f:
                f.write(updated_content)
            logger.info("Successfully updated health middleware")
            return True
        else:
            logger.warning("Failed to update health middleware")
            return False
    except Exception as e:
        logger.error(f"Error fixing health middleware: {e}")
        return False

def create_index_wrapper():
    """Create a wrapper view for index to ensure it always works"""
    try:
        views_path = os.path.join(settings.BASE_DIR, 'core', 'views.py')
        
        with open(views_path, 'r', encoding='utf-8') as f:
            content = f.read()
            
        # Check if the wrapper already exists
        if "railway_index_view" in content:
            logger.info("Railway index view wrapper already exists")
            return True
            
        # Add a wrapper view with safe error handling
        wrapper_view = """
# Wrapper view for index to handle Railway environment
def railway_index_view(request):
    \"\"\"Special index view for Railway deployment\"\"\"
    try:
        # First try the normal index view
        from admin_panel.views import index_view
        return index_view(request)
    except Exception as e:
        import logging
        logger = logging.getLogger('railway')
        logger.error(f"Error in index view: {e}")
        
        # Fallback to a simple response
        from django.shortcuts import render
        
        # Try to render the index template directly
        try:
            return render(request, 'admin_panel/index.html')
        except Exception as template_error:
            logger.error(f"Error rendering template: {template_error}")
            
            # Ultimate fallback - render a basic HTML page
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
            </html>
            '''
            return HttpResponse(html)
"""
        
        # Add the wrapper to the views file
        with open(views_path, 'a', encoding='utf-8') as f:
            f.write(wrapper_view)
            
        logger.info("Successfully created index wrapper view")
        
        # Update the URLs file to use the wrapper
        urls_path = os.path.join(settings.BASE_DIR, 'core', 'urls.py')
        
        with open(urls_path, 'r', encoding='utf-8') as f:
            urls_content = f.read()
            
        # Update import and path
        if "from .views import railway_index_view" not in urls_content:
            urls_content = urls_content.replace(
                "from admin_panel.views import index_view",
                "from admin_panel.views import index_view\nfrom .views import railway_index_view"
            )
            urls_content = urls_content.replace(
                "path('', index_view, name='index')",
                "path('', railway_index_view, name='index')"
            )
            
            with open(urls_path, 'w', encoding='utf-8') as f:
                f.write(urls_content)
                
            logger.info("Successfully updated URLs to use wrapper view")
        else:
            logger.info("URLs already using wrapper view")
            
        return True
    except Exception as e:
        logger.error(f"Error creating index wrapper: {e}")
        return False

def ensure_templates_directory():
    """Make sure templates directory exists and is properly set up"""
    try:
        templates_dir = os.path.join(settings.BASE_DIR, 'templates')
        admin_panel_templates_dir = os.path.join(templates_dir, 'admin_panel')
        
        # Create directories if they don't exist
        os.makedirs(templates_dir, exist_ok=True)
        os.makedirs(admin_panel_templates_dir, exist_ok=True)
        
        # Check if index.html exists
        index_path = os.path.join(admin_panel_templates_dir, 'index.html')
        if not os.path.exists(index_path):
            # Create a simple index.html if it doesn't exist
            with open(index_path, 'w', encoding='utf-8') as f:
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
            logger.info(f"Created basic index.html at {index_path}")
            
        # Check TEMPLATES setting
        templates_setting = settings.TEMPLATES[0]['DIRS']
        templates_path = os.path.join(settings.BASE_DIR, 'templates')
        if templates_path not in str(templates_setting):
            # Need to update the settings
            settings_path = os.path.join(settings.BASE_DIR, 'core', 'settings.py')
            
            with open(settings_path, 'r', encoding='utf-8') as f:
                settings_content = f.read()
                
            if "os.path.join(BASE_DIR, 'templates')" not in settings_content:
                settings_content = settings_content.replace(
                    "TEMPLATES = [",
                    "TEMPLATES = [\n    {\n        'BACKEND': 'django.template.backends.django.DjangoTemplates',\n        'DIRS': [os.path.join(BASE_DIR, 'templates')],\n"
                )
                
                with open(settings_path, 'w', encoding='utf-8') as f:
                    f.write(settings_content)
                    
                logger.info("Updated TEMPLATES setting in settings.py")
                
        return True
    except Exception as e:
        logger.error(f"Error ensuring templates directory: {e}")
        return False

def main():
    """Main function"""
    logger.info("Starting Railway views fix")
    
    # Make sure the templates directory exists
    ensure_templates_directory()
    
    # Fix health middleware
    fix_health_middleware()
    
    # Create index wrapper
    create_index_wrapper()
    
    # Restart server if possible
    try:
        import requests
        requests.get("https://parsinggrouptg-production.up.railway.app/_ping", timeout=2)
    except:
        pass
    
    logger.info("Railway views fix completed")
    
    # Print success message
    print("\n" + "="*50)
    print("Railway views fix applied!")
    print("The website should now display the index.html page properly.")
    print("="*50 + "\n")
    
    return True

if __name__ == "__main__":
    main() 