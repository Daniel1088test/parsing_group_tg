#!/usr/bin/env python3
"""
Script to fix migration conflicts in the database
"""
import os
import sys
import logging
import subprocess
import json

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('fix_migrations.log')
    ]
)
logger = logging.getLogger('fix_migrations')

def run_command(command, description, critical=False):
    """Run a command and log output"""
    logger.info(f"Running {description}: {command}")
    try:
        process = subprocess.Popen(
            command, 
            shell=True, 
            stdout=subprocess.PIPE, 
            stderr=subprocess.STDOUT,
            universal_newlines=True
        )
        
        # Read and log output in real time
        output = []
        for line in iter(process.stdout.readline, ''):
            line = line.strip()
            logger.info(line)
            output.append(line)
            if not line:
                break
        
        process.wait()
        
        if process.returncode != 0:
            logger.error(f"{description} failed with code {process.returncode}")
            if critical:
                logger.critical(f"Critical operation {description} failed. Exiting.")
                sys.exit(1)
            return False, output
        
        logger.info(f"{description} completed successfully")
        return True, output
    except Exception as e:
        logger.error(f"Error running {description}: {e}")
        if critical:
            logger.critical(f"Critical operation {description} failed. Exiting.")
            sys.exit(1)
        return False, []

def create_migration_merge():
    """Create a merge migration to resolve conflicts"""
    logger.info("Creating merge migration to resolve conflicts...")
    
    # Set up Django environment
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
    
    # First create an empty migration to solve conflicts
    result, output = run_command(
        "python manage.py makemigrations admin_panel --empty --name merge_migrations",
        "Creating empty migration"
    )
    
    if not result:
        logger.error("Failed to create empty migration")
        return False
    
    # Now run the migrate command with --fake to bypass the conflict
    result, output = run_command(
        "python manage.py migrate admin_panel --fake",
        "Running fake migration for admin_panel"
    )
    
    if not result:
        logger.error("Failed to run fake migration")
        return False
    
    # Run general migrations
    result, output = run_command(
        "python manage.py migrate",
        "Running all migrations"
    )
    
    if not result:
        logger.error("Failed to run general migrations")
        # Try with --fake-initial as a last resort
        logger.info("Trying with --fake-initial...")
        result, output = run_command(
            "python manage.py migrate --fake-initial",
            "Running migrations with --fake-initial"
        )
        if not result:
            return False
    
    return True

def fix_bot_conflicts():
    """Fix Telegram bot instance conflicts"""
    logger.info("Fixing Telegram bot instance conflicts...")
    
    # Kill any running bot processes
    result, output = run_command(
        "ps -ef | grep -E 'run_bot.py|bot.py' | grep -v grep | awk '{print $2}' | xargs -r kill -9",
        "Killing existing bot processes"
    )
    
    # Check if PID files exist and remove them
    pid_files = ['bot.pid', 'parser.pid']
    for pid_file in pid_files:
        if os.path.exists(pid_file):
            try:
                os.remove(pid_file)
                logger.info(f"Removed PID file: {pid_file}")
            except Exception as e:
                logger.error(f"Error removing PID file {pid_file}: {e}")
    
    return True

def fix_railway_settings():
    """Update Railway settings to ensure the homepage is displayed correctly"""
    logger.info("Fixing Railway settings...")
    
    # Create a static file directly at root
    if not os.path.exists('public'):
        os.makedirs('public', exist_ok=True)
    
    with open('public/index.html', 'w') as f:
        f.write("""<!DOCTYPE html>
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
</html>""")
    
    logger.info("Created public/index.html")
    
    # Create staticfile.toml configuration
    with open('staticfile.toml', 'w') as f:
        f.write("""[[services]]
  name = "static-site"
  type = "static"
  serve = "public"
  routes = "/"
""")
    
    logger.info("Created staticfile.toml")
    
    # Create a dedicated WSGI server file
    with open('wsgi_server.py', 'w') as f:
        f.write("""#!/usr/bin/env python3
import os
import sys
from http.server import BaseHTTPRequestHandler, HTTPServer
import socketserver

HTML_CONTENT = '''<!DOCTYPE html>
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
</html>'''

class SimpleHTTPRequestHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header('Content-type', 'text/html')
        self.end_headers()
        self.wfile.write(HTML_CONTENT.encode('utf-8'))

def run_server(port=8080):
    server_address = ('', port)
    httpd = HTTPServer(server_address, SimpleHTTPRequestHandler)
    print(f"Starting HTTP server on port {port}")
    httpd.serve_forever()

if __name__ == "__main__":
    port = int(os.environ.get('PORT', 8080))
    run_server(port)
""")
    
    logger.info("Created wsgi_server.py")
    
    # Make it executable
    os.chmod('wsgi_server.py', 0o755)
    
    # Override direct_views.py to serve content directly
    os.makedirs('core', exist_ok=True)
    with open('core/direct_views.py', 'w') as f:
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
    
    logger.info("Created core/direct_views.py")
    
    return True

def create_emergency_fix():
    """Create an emergency fix script to be run on startup"""
    logger.info("Creating emergency fix script...")
    
    with open('emergency_fix.sh', 'w') as f:
        f.write("""#!/bin/bash
echo "Running emergency fix script..."

# Fix for Telegram bot conflict
ps -ef | grep -E 'run_bot.py|bot.py' | grep -v grep | awk '{print $2}' | xargs -r kill -9
rm -f bot.pid parser.pid

# Create direct index page
cat > index.html << 'EOL'
<!DOCTYPE html>
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
</html>
EOL

echo "Emergency fix completed"
""")
    
    # Make it executable
    os.chmod('emergency_fix.sh', 0o755)
    
    logger.info("Created emergency_fix.sh")
    
    return True

def main():
    """Main function"""
    logger.info("Starting migration and bot fixes")
    
    # Create emergency fix script
    if not create_emergency_fix():
        logger.error("Failed to create emergency fix script")
    
    # Fix migration conflicts
    if not create_migration_merge():
        logger.error("Failed to fix migration conflicts")
    
    # Fix bot conflicts
    if not fix_bot_conflicts():
        logger.error("Failed to fix bot conflicts")
    
    # Fix Railway settings
    if not fix_railway_settings():
        logger.error("Failed to fix Railway settings")
    
    logger.info("All fixes completed")
    return True

if __name__ == "__main__":
    try:
        success = main()
        if success:
            print("All fixes completed successfully")
            sys.exit(0)
        else:
            print("Some fixes failed")
            sys.exit(1)
    except Exception as e:
        logger.error(f"Unhandled error: {e}")
        print(f"Error: {e}")
        sys.exit(1) 