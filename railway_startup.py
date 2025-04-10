#!/usr/bin/env python
import os
import sys
import subprocess
import time
import logging
import threading
import shutil

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('railway_startup.log'),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger('railway_startup')

# Function to run a command and log output
def run_command(command, description, critical=False):
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
        for line in iter(process.stdout.readline, ''):
            logger.info(line.strip())
            if not line:
                break
        
        process.wait()
        
        if process.returncode != 0:
            logger.error(f"{description} failed with code {process.returncode}")
            if critical:
                logger.critical(f"Critical operation {description} failed. Exiting.")
                sys.exit(1)
            return False
        
        logger.info(f"{description} completed successfully")
        return True
    except Exception as e:
        logger.error(f"Error running {description}: {e}")
        if critical:
            logger.critical(f"Critical operation {description} failed. Exiting.")
            sys.exit(1)
        return False

# Apply all database fixes
def apply_fixes():
    # Apply database and template fixes (in order of dependency)
    fixes = [
        ("python fix_templates_and_aiohttp.py", "Template and AIOHTTP fixes"),
        ("python fix_railway_views.py", "Railway views fixes"),
        ("python fix_multiple_fields.py", "Multiple fields fixes"),
        ("python fix_admin_query.py", "Admin query fixes"),
        ("python fix_railway_migrations.py", "Railway migrations fixes"),
        ("python fix_session_migration.py", "Session migration fixes"),
        ("python fix_all_issues.py", "General issue fixes"),
        ("python fix_integration_issues.py", "Integration issue fixes", False),
        ("python fix_database_connection.py", "Database connection fixes", False)
    ]
    
    for fix in fixes:
        if len(fix) == 3:
            command, description, critical = fix
        else:
            command, description = fix
            critical = False
        run_command(command, description, critical)

# Run Django migrations
def run_migrations():
    run_command("python manage.py makemigrations", "Make migrations")
    run_command("python manage.py migrate", "Apply migrations", True)
    run_command("python manage.py collectstatic --noinput", "Collect static files")

# Start the bot in a separate thread
def start_bot():
    logger.info("Starting Telegram bot...")
    return subprocess.Popen(["python", "run_bot.py"])

# Start the parser in a separate thread
def start_parser():
    logger.info("Starting Telegram parser...")
    return subprocess.Popen(["python", "run_parser.py"])

# Ensure templates are properly set up
def ensure_templates():
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))
    templates_dir = os.path.join(BASE_DIR, 'templates')
    admin_panel_dir = os.path.join(templates_dir, 'admin_panel')
    
    # Ensure templates directory exists
    os.makedirs(templates_dir, exist_ok=True)
    os.makedirs(admin_panel_dir, exist_ok=True)
    
    # Log the template structure
    logger.info(f"Templates directory: {templates_dir}")
    if os.path.exists(templates_dir):
        logger.info(f"Template files: {os.listdir(templates_dir)}")
        if os.path.exists(admin_panel_dir):
            logger.info(f"Admin panel template files: {os.listdir(admin_panel_dir)}")
    
    # Make sure media and static directories exist
    media_dir = os.path.join(BASE_DIR, 'media')
    static_dir = os.path.join(BASE_DIR, 'static')
    staticfiles_dir = os.path.join(BASE_DIR, 'staticfiles')
    
    os.makedirs(media_dir, exist_ok=True)
    os.makedirs(os.path.join(media_dir, 'messages'), exist_ok=True)
    os.makedirs(static_dir, exist_ok=True)
    os.makedirs(staticfiles_dir, exist_ok=True)
    
    # Check permissions on template files
    try:
        for root, dirs, files in os.walk(templates_dir):
            for file in files:
                file_path = os.path.join(root, file)
                os.chmod(file_path, 0o644)  # Make readable
                logger.info(f"Set permissions for {file_path}")
            for directory in dirs:
                dir_path = os.path.join(root, directory)
                os.chmod(dir_path, 0o755)  # Make executable (for directories)
                logger.info(f"Set permissions for directory {dir_path}")
    except Exception as e:
        logger.warning(f"Error setting permissions: {e}")

# Main function to orchestrate startup
def main():
    logger.info("Starting Railway deployment setup")
    
    # Check environment variables
    port = os.environ.get('PORT', '8000')
    logger.info(f"Using PORT: {port}")
    
    # Set important environment variables
    os.environ['DJANGO_SETTINGS_MODULE'] = 'core.settings'
    
    # Ensure templates are properly set up
    ensure_templates()
    
    # Apply fixes
    apply_fixes()
    
    # Run migrations
    run_migrations()
    
    # Create health check files
    logger.info("Creating health check files...")
    for filename in ["health.txt", "health.html", "healthz.txt", "healthz.html"]:
        with open(filename, "w") as f:
            f.write("OK")
    
    # Start bot and parser processes as background processes
    bot_process = start_bot()
    parser_process = start_parser()
    
    # Start web server (this will block until the server stops)
    gunicorn_command = f"gunicorn core.wsgi:application --preload --max-requests 1000 --max-requests-jitter 100 --workers 2 --threads 2 --timeout 60 --bind 0.0.0.0:{port}"
    logger.info(f"Starting web server: {gunicorn_command}")
    web_process = subprocess.Popen(gunicorn_command, shell=True)
    
    try:
        # Keep the main process running
        web_process.wait()
    except KeyboardInterrupt:
        logger.info("Received keyboard interrupt, shutting down...")
    finally:
        # Terminate child processes
        for process in [bot_process, parser_process, web_process]:
            if process and process.poll() is None:
                process.terminate()
                process.wait()
        
        logger.info("All processes terminated")

if __name__ == "__main__":
    main()
