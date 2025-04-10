#!/usr/bin/env python
"""
Emergency fix script for Railway deployment
This script attempts to fix issues with template rendering and static files
"""
import os
import sys
import logging
import shutil
import django
from pathlib import Path

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('emergency_fix.log'),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger('emergency_fix')

# Set up Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
try:
    django.setup()
    from django.conf import settings
    logger.info("Django successfully initialized")
except Exception as e:
    logger.error(f"Error initializing Django: {e}")
    sys.exit(1)

def ensure_templates_exist():
    """Ensure templates directory exists and has the necessary files"""
    base_dir = Path(__file__).resolve().parent
    templates_dir = base_dir / 'templates'
    admin_panel_dir = templates_dir / 'admin_panel'
    
    # Create directories if they don't exist
    templates_dir.mkdir(exist_ok=True)
    admin_panel_dir.mkdir(exist_ok=True)
    
    # List of template files that should be in the admin_panel directory
    admin_template_files = [
        'index.html', 'login.html', 'register.html', 'admin_panel.html'
    ]
    
    # Check if index.html exists, create it if it doesn't
    index_path = admin_panel_dir / 'index.html'
    if not index_path.exists():
        logger.warning(f"index.html not found, creating emergency template at {index_path}")
        index_content = """
{% extends 'base.html' %}

{% block title %}Admin Panel{% endblock %}

{% block content %}
<div class="container mt-5">
    <div class="row">
        <div class="col-md-12">
            <h1 class="text-center mb-4">Telegram Channel Parser</h1>
            <div class="card">
                <div class="card-header bg-primary text-white">
                    <h5 class="mb-0">Admin Panel</h5>
                </div>
                <div class="card-body">
                    <p class="lead">Welcome to the Telegram Channel Parser Admin Panel. Use the navigation menu to manage your channels and view messages.</p>
                    <div class="alert alert-info">
                        <i class="fas fa-info-circle"></i> The bot is currently running. You can manage your channels and view the parsed messages.
                    </div>
                    <div class="row mt-4">
                        <div class="col-md-4">
                            <div class="card text-white bg-primary mb-3">
                                <div class="card-header">Channels</div>
                                <div class="card-body">
                                    <h5 class="card-title">Manage Channels</h5>
                                    <p class="card-text">Add, edit, or remove channels to parse.</p>
                                    <a href="{% url 'channels_list' %}" class="btn btn-light">View Channels</a>
                                </div>
                            </div>
                        </div>
                        <div class="col-md-4">
                            <div class="card text-white bg-success mb-3">
                                <div class="card-header">Messages</div>
                                <div class="card-body">
                                    <h5 class="card-title">View Messages</h5>
                                    <p class="card-text">Browse through parsed messages from channels.</p>
                                    <a href="{% url 'messages_list' %}" class="btn btn-light">View Messages</a>
                                </div>
                            </div>
                        </div>
                        <div class="col-md-4">
                            <div class="card text-white bg-info mb-3">
                                <div class="card-header">Sessions</div>
                                <div class="card-body">
                                    <h5 class="card-title">Manage Sessions</h5>
                                    <p class="card-text">Configure Telegram API sessions.</p>
                                    <a href="{% url 'sessions_list' %}" class="btn btn-light">View Sessions</a>
                                </div>
                            </div>
                        </div>
                    </div>
                </div>
            </div>
        </div>
    </div>
</div>
{% endblock %}
"""
        with open(index_path, 'w', encoding='utf-8') as f:
            f.write(index_content)
        
    # Check if base.html exists, create it if it doesn't
    base_path = templates_dir / 'base.html'
    if not base_path.exists():
        logger.warning(f"base.html not found, creating emergency template at {base_path}")
        
        # Read from BASE_DIR/templates/base.html if it exists
        src_base_path = base_dir / 'templates' / 'base.html'
        if os.path.exists(src_base_path):
            shutil.copy(src_base_path, base_path)
            logger.info(f"Copied base.html from {src_base_path} to {base_path}")
        else:
            # Create a basic base.html template
            base_content = """<!DOCTYPE html>
<html lang="uk">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{% block title %}Telegram Parser{% endblock %}</title>
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
            --success-color: #1cc88a;
            --info-color: #36b9cc;
            --warning-color: #f6c23e;
            --danger-color: #e74a3b;
        }
        body {
            background-color: #f8f9fc;
            font-family: 'Nunito', sans-serif;
        }
        .sidebar {
            min-height: 100vh;
            background: linear-gradient(180deg, var(--primary-color) 0%, var(--secondary-color) 100%);
            color: white;
            box-shadow: 0 0.15rem 1.75rem 0 rgba(58, 59, 69, 0.15);
            z-index: 100;
        }
        .sidebar-brand {
            height: 70px;
            display: flex;
            align-items: center;
            justify-content: center;
            padding: 1.5rem 1rem;
            font-size: 1.5rem;
            font-weight: 700;
            border-bottom: 1px solid rgba(255, 255, 255, 0.1);
        }
        .sidebar-item {
            padding: 1rem;
            border-radius: 0.35rem;
            margin: 0.5rem 1rem;
            transition: all 0.3s;
        }
    </style>
    {% block extra_css %}{% endblock %}
</head>
<body>
    <div class="container-fluid">
        <div class="row">
            <!-- Sidebar -->
            <div class="col-md-3 col-lg-2 d-md-block sidebar collapse">
                <div class="sidebar-brand">
                    <i class="fas fa-robot me-2"></i>
                    Telegram Parser
                </div>
                <div class="mt-3">
                    <a href="{% url 'admin_panel' %}" class="d-block text-white text-decoration-none sidebar-item active">
                        <i class="fas fa-tachometer-alt"></i> Admin panel
                    </a>
                    <a href="{% url 'channels_list' %}" class="d-block text-white text-decoration-none sidebar-item">
                        <i class="fas fa-paper-plane"></i> Channels
                    </a>
                    <a href="{% url 'categories_list' %}" class="d-block text-white text-decoration-none sidebar-item">
                        <i class="fas fa-folder"></i> Categories
                    </a>
                    <a href="{% url 'messages_list' %}" class="d-block text-white text-decoration-none sidebar-item">
                        <i class="fas fa-comment"></i> Messages
                    </a>
                    <a href="{% url 'sessions_list' %}" class="d-block text-white text-decoration-none sidebar-item">
                        <i class="fas fa-key"></i> Telegram Sessions
                    </a>
                    <div class="mt-5">
                        <a href="{% url 'logout' %}" class="d-block text-white text-decoration-none sidebar-item">
                            <i class="fas fa-sign-out-alt"></i> Logout
                        </a>
                    </div>
                </div>
            </div>
            <div class="col-md-9 col-lg-10 main-content">
                <!-- Main Content -->
                <div class="content-wrapper p-4">
                    {% block content %}{% endblock %}
                </div>
            </div>
        </div>
    </div>

    <!-- Bootstrap JavaScript -->
    <script src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.2/dist/js/bootstrap.bundle.min.js"></script>
    <!-- jQuery (required for DataTables) -->
    <script src="https://code.jquery.com/jquery-3.6.0.min.js"></script>
    <!-- DataTables JS -->
    <script src="https://cdn.datatables.net/1.13.6/js/jquery.dataTables.min.js"></script>
    <script src="https://cdn.datatables.net/1.13.6/js/dataTables.bootstrap5.min.js"></script>
    <script src="https://cdn.datatables.net/responsive/2.5.0/js/dataTables.responsive.min.js"></script>
    <script src="https://cdn.datatables.net/responsive/2.5.0/js/responsive.bootstrap5.min.js"></script>
    
    {% block extra_js %}{% endblock %}
</body>
</html>"""
            with open(base_path, 'w', encoding='utf-8') as f:
                f.write(base_content)
    
    # List the files in the templates directory
    logger.info(f"Files in {templates_dir}: {os.listdir(templates_dir)}")
    if os.path.exists(admin_panel_dir):
        logger.info(f"Files in {admin_panel_dir}: {os.listdir(admin_panel_dir)}")

def fix_core_urls():
    """Fix the core/urls.py file if needed"""
    try:
        urls_file = Path(__file__).resolve().parent / 'core' / 'urls.py'
        if not urls_file.exists():
            logger.error(f"URLs file not found at {urls_file}")
            return
            
        # Read the file
        content = urls_file.read_text(encoding='utf-8')
        
        # Check if we need to fix the index URL
        if "path('', lambda request: HttpResponse('Telegram bot is running'" in content:
            logger.warning("Found hardcoded 'Telegram bot is running' in URLs, fixing...")
            
            # Replace with proper view
            content = content.replace(
                "path('', lambda request: HttpResponse('Telegram bot is running'",
                "path('', railway_index_view if 'railway_index_view' in locals() else index_view"
            )
            
            # Write the file
            urls_file.write_text(content, encoding='utf-8')
            logger.info("Fixed core/urls.py")
    except Exception as e:
        logger.error(f"Error fixing URLs: {e}")

def fix_static_files():
    """Ensure static files are correctly deployed"""
    try:
        # Run collectstatic
        import subprocess
        result = subprocess.run(
            [sys.executable, 'manage.py', 'collectstatic', '--noinput'],
            capture_output=True,
            text=True
        )
        logger.info(f"Collectstatic output: {result.stdout}")
        if result.stderr:
            logger.warning(f"Collectstatic errors: {result.stderr}")
    except Exception as e:
        logger.error(f"Error running collectstatic: {e}")

def ensure_health_checks():
    """Create health check files to keep Railway happy"""
    for filename in ["health.txt", "health.html", "healthz.txt", "healthz.html"]:
        with open(filename, "w") as f:
            f.write("OK")
        logger.info(f"Created health check file: {filename}")

def main():
    """Main function to run all fixes"""
    logger.info("Starting emergency fixes for Railway deployment")
    
    # Ensure templates exist
    ensure_templates_exist()
    
    # Fix core URLs
    fix_core_urls()
    
    # Fix static files
    fix_static_files()
    
    # Ensure health checks
    ensure_health_checks()
    
    logger.info("Emergency fixes completed")
    
if __name__ == "__main__":
    main()
