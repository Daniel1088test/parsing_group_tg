#!/usr/bin/env python
import os
import sys
import subprocess
import time
import logging
import threading

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

# Main function to orchestrate startup
def main():
    logger.info("Starting Railway deployment setup")
    
    # Check environment variables
    port = os.environ.get('PORT', '8000')
    logger.info(f"Using PORT: {port}")
    
    # Apply fixes
    apply_fixes()
    
    # Run migrations
    run_migrations()
    
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
