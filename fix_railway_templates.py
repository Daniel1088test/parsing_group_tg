#!/usr/bin/env python3
"""
Script to fix templates for Railway deployment, ensuring @templates and @index.html work correctly
"""
import os
import sys
import logging
import shutil
import django

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('fix_railway_templates.log')
    ]
)
logger = logging.getLogger('fix_railway_templates')

# Set up Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
try:
    django.setup()
    from django.conf import settings
    logger.info("Django initialized successfully")
except Exception as e:
    logger.error(f"Error initializing Django: {e}")
    sys.exit(1)

def ensure_template_directories():
    """Ensure that all required template directories exist"""
    try:
        # Create required directories
        base_dir = settings.BASE_DIR
        templates_dir = os.path.join(base_dir, 'templates')
        admin_panel_dir = os.path.join(templates_dir, 'admin_panel')
        
        # Create directories with proper permissions
        os.makedirs(templates_dir, exist_ok=True)
        os.makedirs(admin_panel_dir, exist_ok=True)
        
        # Set proper permissions
        os.chmod(templates_dir, 0o755)
        os.chmod(admin_panel_dir, 0o755)
        
        logger.info(f"Created template directories: {templates_dir}, {admin_panel_dir}")
        
        # Create index.html symlink in root if it doesn't exist
        index_path = os.path.join(base_dir, 'index.html')
        admin_index = os.path.join(admin_panel_dir, 'index.html')
        
        # Check if we need to create/copy index.html
        if not os.path.exists(admin_index):
            # Check if we have the admin panel index.html attached to the project
            logger.info("Admin panel index.html not found, trying to create it")
            
            # Create a basic index.html if one doesn't exist
            with open(admin_index, 'w') as f:
                f.write("""{% load custom_filters %}
{% load static %}
<!DOCTYPE html>
<html lang="uk">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Telegram Parser | Monitoring channels</title>    

    <!-- Bootstrap 5 CSS -->
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.2/dist/css/bootstrap.min.css" rel="stylesheet">
    <!-- Font Awesome -->
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.2/css/all.min.css">
    <!-- Add base URL for media files -->
    <base href="/">
    
    <style>
        body {
            background-color: #f8f9fc;
            font-family: 'Nunito', sans-serif;
        }
        
        .navbar {
            background: linear-gradient(to right, #4e73df, #8e54e9);
            box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
        }
        
        .navbar-brand {
            font-weight: 700;
            font-size: 1.5rem;
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
        </div>
    </nav>

    <div class="container py-5">
        <div class="row justify-content-center">
            <div class="col-md-8">
                <div class="card shadow">
                    <div class="card-body text-center p-5">
                        <h1 class="display-4 mb-4">Telegram bot is running</h1>
                        <p class="lead">The Telegram parsing service is active and monitoring channels.</p>
                        <div class="mt-4">
                            <a href="/admin_panel/" class="btn btn-primary btn-lg">
                                <i class="fas fa-tachometer-alt me-2"></i> Go to Admin Panel
                            </a>
                            <a href="https://t.me/chan_parsing_mon_bot" class="btn btn-info btn-lg ms-2">
                                <i class="fab fa-telegram me-2"></i> Open Telegram Bot
                            </a>
                        </div>
                    </div>
                </div>
            </div>
        </div>
    </div>

    <!-- jQuery and Bootstrap JS -->
    <script src="https://code.jquery.com/jquery-3.7.1.min.js"></script>
    <script src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.2/dist/js/bootstrap.bundle.min.js"></script>
</body>
</html>""")
            logger.info(f"Created admin panel index.html: {admin_index}")
        
        # Create symlink or copy index.html to root if needed
        if not os.path.exists(index_path):
            try:
                # Try to create a symlink first
                os.symlink(admin_index, index_path)
                logger.info(f"Created symlink to index.html at root: {index_path}")
            except (OSError, AttributeError):
                # If symlink creation fails, copy the file instead
                shutil.copy2(admin_index, index_path)
                logger.info(f"Copied index.html to root: {index_path}")
        
        # Create base.html if it doesn't exist
        base_html = os.path.join(templates_dir, 'base.html')
        if not os.path.exists(base_html):
            with open(base_html, 'w') as f:
                f.write("""<!DOCTYPE html>
<html lang="uk">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{% block title %}Telegram Parser{% endblock %}</title>
    <!-- Bootstrap 5 CSS -->
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.2/dist/css/bootstrap.min.css" rel="stylesheet">
    <!-- Font Awesome -->
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.2/css/all.min.css">
    <style>
        body {
            background-color: #f8f9fc;
            font-family: 'Nunito', sans-serif;
        }
        
        .navbar {
            background: linear-gradient(to right, #4e73df, #8e54e9);
            box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
        }
        
        .navbar-brand {
            font-weight: 700;
            font-size: 1.5rem;
        }
    </style>
    {% block extra_css %}{% endblock %}
</head>
<body>
    <!-- Navigation -->
    <nav class="navbar navbar-expand-lg navbar-dark">
        <div class="container">
            <a class="navbar-brand" href="/">
                <i class="fas fa-robot me-2"></i>
                Telegram Parser
            </a>
        </div>
    </nav>

    {% block content %}
    <div class="container py-5">
        <div class="row justify-content-center">
            <div class="col-md-8">
                <div class="card shadow">
                    <div class="card-body text-center p-5">
                        <h1 class="display-4 mb-4">Telegram bot is running</h1>
                        <p class="lead">The Telegram parsing service is active and monitoring channels.</p>
                    </div>
                </div>
            </div>
        </div>
    </div>
    {% endblock %}

    <!-- jQuery and Bootstrap JS -->
    <script src="https://code.jquery.com/jquery-3.7.1.min.js"></script>
    <script src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.2/dist/js/bootstrap.bundle.min.js"></script>
    {% block extra_js %}{% endblock %}
</body>
</html>""")
            logger.info(f"Created base.html: {base_html}")
        
        return True
    except Exception as e:
        logger.error(f"Error ensuring template directories: {e}")
        return False

def fix_middleware_for_railway():
    """Add middleware to support Railway template resolution"""
    try:
        # Check if we need to create the middleware
        middleware_file = os.path.join(settings.BASE_DIR, 'core', 'railway_middleware.py')
        if not os.path.exists(middleware_file):
            with open(middleware_file, 'w') as f:
                f.write("""import os
import logging
from django.conf import settings

logger = logging.getLogger('railway_middleware')

class RailwayTemplateMiddleware:
    \"\"\"Middleware to support proper template resolution in Railway deployment\"\"\"
    
    def __init__(self, get_response):
        self.get_response = get_response
        logger.info("RailwayTemplateMiddleware initialized")
        
        # Ensure template dirs are updated
        from django.template.engine import Engine
        for engine in Engine.get_default().engine.template_directories:
            logger.info(f"Template directory: {engine}")
        
        # Check if index.html exists at root
        index_path = os.path.join(settings.BASE_DIR, 'index.html')
        if os.path.exists(index_path):
            logger.info(f"Root index.html exists: {index_path}")
        else:
            logger.warning(f"Root index.html not found: {index_path}")
    
    def __call__(self, request):
        # Process request
        response = self.get_response(request)
        return response
""")
            logger.info(f"Created Railway middleware: {middleware_file}")
        
        # Check if the middleware is in settings.py
        middleware_setting = 'core.railway_middleware.RailwayTemplateMiddleware'
        settings_file = os.path.join(settings.BASE_DIR, 'core', 'settings.py')
        
        with open(settings_file, 'r') as f:
            content = f.read()
        
        if middleware_setting not in content:
            # Add the middleware to settings.py
            import re
            pattern = r'(MIDDLEWARE\s*=\s*\[(\s*\'[^\']+\',)*\s*)'
            replacement = f"\\1    '{middleware_setting}',\n"
            new_content = re.sub(pattern, replacement, content)
            
            with open(settings_file, 'w') as f:
                f.write(new_content)
            
            logger.info(f"Added Railway middleware to settings.py: {middleware_setting}")
        
        return True
    except Exception as e:
        logger.error(f"Error fixing middleware for Railway: {e}")
        return False

def modify_railway_startup():
    """Update railway_startup.py to ensure our fix_railway_templates.py is run"""
    try:
        startup_file = os.path.join(settings.BASE_DIR, 'railway_startup.py')
        if os.path.exists(startup_file):
            with open(startup_file, 'r') as f:
                content = f.read()
            
            # Look for apply_fixes function and add our fix
            if 'fix_railway_templates.py' not in content:
                import re
                pattern = r'(def apply_fixes\(\):\s*# Apply database and template fixes.*?\[.*?)(\])'
                replacement = r'\1        ("python fix_railway_templates.py", "Railway template fixes", True),\n    \2'
                new_content = re.sub(pattern, replacement, content, flags=re.DOTALL)
                
                with open(startup_file, 'w') as f:
                    f.write(new_content)
                
                logger.info(f"Updated railway_startup.py to include fix_railway_templates.py")
        
        return True
    except Exception as e:
        logger.error(f"Error modifying railway_startup.py: {e}")
        return False

def update_urls_for_root_index():
    """Update urls.py to correctly serve index.html at root"""
    try:
        urls_file = os.path.join(settings.BASE_DIR, 'core', 'urls.py')
        if os.path.exists(urls_file):
            with open(urls_file, 'r') as f:
                content = f.read()
            
            # Add direct file response for index.html
            if 'serve_root_index' not in content:
                import re
                # Add the function for serving index.html
                imports_pattern = r'from django.http import (.*)'
                if 'FileResponse' not in content:
                    imports_replacement = r'from django.http import \1, FileResponse'
                    content = re.sub(imports_pattern, imports_replacement, content)
                
                # Add new function for serving root index.html
                view_pattern = r'(def health_check.*?\n\S)'
                view_replacement = r"""def serve_root_index(request):
    """Serve index.html directly from root directory"""
    import os
    from django.conf import settings
    index_path = os.path.join(settings.BASE_DIR, 'index.html')
    if os.path.exists(index_path):
        return FileResponse(open(index_path, 'rb'), content_type='text/html')
    return railway_index_view(request)

\1"""
                content = re.sub(view_pattern, view_replacement, content, flags=re.DOTALL)
                
                # Update the urlpatterns
                urlpatterns_pattern = r'(path\(\'\', railway_index_view.*?name=\'index\'\))'
                urlpatterns_replacement = r'path(\'\', serve_root_index, name=\'index\')'
                content = re.sub(urlpatterns_pattern, urlpatterns_replacement, content)
                
                with open(urls_file, 'w') as f:
                    f.write(content)
                
                logger.info(f"Updated urls.py to serve index.html from root")
        
        return True
    except Exception as e:
        logger.error(f"Error updating urls.py: {e}")
        return False

def main():
    """Main function"""
    logger.info("Starting Railway templates fix")
    
    # Make sure template directories exist and index.html is in place
    ensure_template_directories()
    
    # Add middleware to support Railway template resolution
    fix_middleware_for_railway()
    
    # Update railway_startup.py to run our fix script
    modify_railway_startup()
    
    # Update urls.py to correctly serve index.html at root
    update_urls_for_root_index()
    
    logger.info("Railway templates fix completed")
    return True

if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        logger.error(f"Unhandled error: {e}")
        sys.exit(1) 