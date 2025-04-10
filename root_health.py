#!/usr/bin/env python3
"""
Script to generate direct HTML files at the root for Railway
"""
import os
import sys
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('root_health.log')
    ]
)
logger = logging.getLogger('root_health')

def create_direct_html_files():
    """Create direct HTML files at the root directory"""
    try:
        # HTML content for the homepage
        homepage_html = """<!DOCTYPE html>
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
</html>"""

        # Create index.html
        with open('index.html', 'w') as f:
            f.write(homepage_html)
        logger.info("Created index.html")
        
        # Create a simpler version to be served by Railway's static serving
        with open('static/index.html', 'w') as f:
            f.write(homepage_html)
        logger.info("Created static/index.html")
        
        # Create another copy in staticfiles directory
        with open('staticfiles/index.html', 'w') as f:
            f.write(homepage_html)
        logger.info("Created staticfiles/index.html")
        
        # Also create a simple HTML health check file
        health_html = """<!DOCTYPE html>
<html>
<head>
    <title>Health Check</title>
    <meta charset="UTF-8">
</head>
<body>
    <h1>Health Check: OK</h1>
    <p>The service is running correctly.</p>
</body>
</html>"""
        
        # Create health check files
        for filename in ['health.html', 'healthz.html']:
            with open(filename, 'w') as f:
                f.write(health_html)
            with open(f'static/{filename}', 'w') as f:
                f.write(health_html)
            with open(f'staticfiles/{filename}', 'w') as f:
                f.write(health_html)
        logger.info("Created health check HTML files")
        
        # Ensure correct permissions
        for filename in ['index.html', 'health.html', 'healthz.html']:
            try:
                os.chmod(filename, 0o644)
                logger.info(f"Set permissions for {filename}")
            except Exception as e:
                logger.warning(f"Failed to set permissions for {filename}: {e}")
        
        return True
    except Exception as e:
        logger.error(f"Error creating direct HTML files: {e}")
        return False

def ensure_directories_exist():
    """Ensure static directories exist"""
    try:
        for directory in ['static', 'static/img', 'staticfiles', 'staticfiles/img']:
            if not os.path.exists(directory):
                os.makedirs(directory, exist_ok=True)
                logger.info(f"Created directory: {directory}")
        return True
    except Exception as e:
        logger.error(f"Error ensuring directories exist: {e}")
        return False

def main():
    """Main function"""
    logger.info("Starting root health generation")
    
    # Ensure directories exist
    if not ensure_directories_exist():
        logger.error("Failed to ensure directories exist")
        return False
    
    # Create direct HTML files
    if not create_direct_html_files():
        logger.error("Failed to create direct HTML files")
        return False
    
    logger.info("Root health generation completed successfully")
    return True

if __name__ == "__main__":
    try:
        success = main()
        if success:
            print("Root health generation completed successfully")
            sys.exit(0)
        else:
            print("Root health generation failed")
            sys.exit(1)
    except Exception as e:
        logger.error(f"Unhandled error: {e}")
        print(f"Error: {e}")
        sys.exit(1) 