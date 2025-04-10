#!/usr/bin/env python3
"""
Direct fix script for Railway deployment - ensures the homepage works correctly
"""
import os
import sys
import logging
import shutil

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('direct_railway_fix.log')
    ]
)
logger = logging.getLogger('direct_railway_fix')

def create_direct_view():
    """Create a direct view function to serve HTML content"""
    try:
        # First check if we need to create the file
        views_file = 'core/direct_views.py'
        if os.path.exists(views_file):
            logger.info(f"File {views_file} already exists, skipping creation")
            return True
        
        with open(views_file, 'w') as f:
            f.write("""from django.http import HttpResponse

def direct_index_view(request):
    \"\"\"Serve the index page directly as HTML content\"\"\"
    html = \"\"\"<!DOCTYPE html>
<html lang="uk">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Telegram Parser | Railway Deployment</title>
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.2/dist/css/bootstrap.min.css" rel="stylesheet">
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.2/css/all.min.css">
    <style>
        body {
            background-color: #f8f9fc;
            font-family: 'Nunito', sans-serif;
            min-height: 100vh;
            display: flex;
            flex-direction: column;
        }
        
        .navbar {
            background: linear-gradient(to right, #4e73df, #8e54e9);
            box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
        }
        
        .navbar-brand {
            font-weight: 700;
            font-size: 1.5rem;
        }
        
        .main-content {
            flex: 1;
            display: flex;
            align-items: center;
            justify-content: center;
        }
        
        .bot-status-card {
            border-radius: 10px;
            overflow: hidden;
            box-shadow: 0 10px 20px rgba(0, 0, 0, 0.1);
            transition: all 0.3s ease;
            max-width: 600px;
            width: 100%;
        }
        
        .bot-status-card:hover {
            transform: translateY(-5px);
            box-shadow: 0 15px 30px rgba(0, 0, 0, 0.2);
        }
        
        .status-indicator {
            width: 20px;
            height: 20px;
            border-radius: 50%;
            background-color: #2ecc71;
            display: inline-block;
            margin-right: 8px;
            animation: pulse 2s infinite;
        }
        
        @keyframes pulse {
            0% {
                box-shadow: 0 0 0 0 rgba(46, 204, 113, 0.4);
            }
            70% {
                box-shadow: 0 0 0 10px rgba(46, 204, 113, 0);
            }
            100% {
                box-shadow: 0 0 0 0 rgba(46, 204, 113, 0);
            }
        }
        
        .footer {
            background-color: #343a40;
            color: rgba(255, 255, 255, 0.8);
            padding: 15px 0;
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
            <div class="ms-auto">
                <a href="/admin_panel/" class="btn btn-light btn-sm">
                    <i class="fas fa-tachometer-alt me-1"></i> Admin Panel
                </a>
            </div>
        </div>
    </nav>

    <!-- Main Content -->
    <div class="main-content">
        <div class="container">
            <div class="row justify-content-center">
                <div class="col-md-10">
                    <div class="bot-status-card">
                        <div class="card-body text-center p-5">
                            <div class="mb-4">
                                <span class="status-indicator"></span>
                                <span class="badge bg-success fs-5">Online</span>
                            </div>
                            <h1 class="display-4 mb-4">Telegram bot is running</h1>
                            <p class="lead mb-4">The Telegram parsing service is active and successfully monitoring channels.</p>
                            <div class="d-grid gap-3 d-sm-flex justify-content-sm-center">
                                <a href="/admin_panel/" class="btn btn-primary btn-lg px-4 gap-3">
                                    <i class="fas fa-tachometer-alt me-2"></i> Go to Admin Panel
                                </a>
                                <a href="https://t.me/chan_parsing_mon_bot" class="btn btn-info btn-lg px-4">
                                    <i class="fab fa-telegram me-2"></i> Open Telegram Bot
                                </a>
                            </div>
                        </div>
                    </div>
                </div>
            </div>
        </div>
    </div>

    <!-- Footer -->
    <footer class="footer text-center">
        <div class="container">
            <p class="mb-0">&copy; 2025 Telegram Parser. All rights reserved.</p>
        </div>
    </footer>

    <script src="https://code.jquery.com/jquery-3.7.1.min.js"></script>
    <script src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.2/dist/js/bootstrap.bundle.min.js"></script>
</body>
</html>\"\"\"
    return HttpResponse(html, content_type='text/html')
""")
        logger.info(f"Created direct view file: {views_file}")
        return True
    except Exception as e:
        logger.error(f"Error creating direct view: {e}")
        return False

def update_urls_file():
    """Update urls.py to use our direct view"""
    try:
        urls_file = 'core/urls.py'
        
        # Check if file exists
        if not os.path.exists(urls_file):
            logger.error(f"URLs file not found: {urls_file}")
            return False
        
        # Read the file
        with open(urls_file, 'r') as f:
            content = f.read()
        
        # Check if we've already updated it
        if 'direct_index_view' in content:
            logger.info("URLs file already updated, skipping")
            return True
        
        # Update imports
        import_line = "from .direct_views import direct_index_view"
        if import_line not in content:
            # Find the imports section and add our import
            import_section_end = content.find("# Ensure the views module is imported correctly")
            if import_section_end > 0:
                content = content[:import_section_end] + import_line + "\n\n" + content[import_section_end:]
            else:
                # Fallback to adding after the last import
                last_import = content.rfind("import ")
                last_import_end = content.find("\n", last_import)
                if last_import_end > 0:
                    content = content[:last_import_end+1] + "\n" + import_line + content[last_import_end+1:]
        
        # Update the root URL pattern to use our direct view
        url_pattern_start = content.find("urlpatterns = [")
        if url_pattern_start > 0:
            url_pattern_end = content.find("path('',", url_pattern_start)
            next_line_end = content.find("\n", url_pattern_end)
            
            if url_pattern_end > 0 and next_line_end > 0:
                # Replace the existing index path with our direct view
                new_pattern = "    path('', direct_index_view, name='index'),\n"
                content = content[:url_pattern_end] + new_pattern + content[next_line_end+1:]
        
        # Write the updated content back to the file
        with open(urls_file, 'w') as f:
            f.write(content)
        
        logger.info(f"Updated URLs file: {urls_file}")
        return True
    except Exception as e:
        logger.error(f"Error updating URLs file: {e}")
        return False

def main():
    """Main function"""
    logger.info("Starting direct Railway fix")
    
    # Create direct view function
    if not create_direct_view():
        logger.error("Failed to create direct view")
        return False
    
    # Update URLs configuration
    if not update_urls_file():
        logger.error("Failed to update URLs configuration")
        return False
    
    logger.info("Direct Railway fix completed successfully")
    return True

if __name__ == "__main__":
    try:
        success = main()
        if success:
            print("Direct Railway fix completed successfully")
            sys.exit(0)
        else:
            print("Direct Railway fix failed")
            sys.exit(1)
    except Exception as e:
        logger.error(f"Unhandled error: {e}")
        print(f"Error: {e}")
        sys.exit(1) 