#!/usr/bin/env python3
import os
import sys
import subprocess
import time
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler('railway_startup.log')
    ]
)
logger = logging.getLogger('railway_startup')

def run_fixes():
    """Run all fix scripts"""
    logger.info("Running fix scripts...")
    
    # Run template fixes
    subprocess.run(["python", "fix_templates_and_aiohttp.py"], check=False)
    
    # Run database field fixes
    subprocess.run(["python", "fix_multiple_fields.py"], check=False)
    
    # Run admin query fixes
    subprocess.run(["python", "fix_admin_query.py"], check=False)
    
    # Run migrations
    subprocess.run(["python", "manage.py", "migrate", "--noinput"], check=False)
    
    # Collect static files
    subprocess.run(["python", "manage.py", "collectstatic", "--noinput"], check=False)
    
    logger.info("Fix scripts completed")

def create_health_files():
    """Create health check files"""
    logger.info("Creating health check files...")
    
    # Create health.txt
    with open('health.txt', 'w') as f:
        f.write('OK')
    
    # Create healthz.txt
    with open('healthz.txt', 'w') as f:
        f.write('OK')
    
    # Create health.html
    with open('health.html', 'w') as f:
        f.write('<html><body>OK</body></html>')
    
    # Create healthz.html
    with open('healthz.html', 'w') as f:
        f.write('<html><body>OK</body></html>')
    
    logger.info("Health check files created")

def start_gunicorn():
    """Start Gunicorn server"""
    logger.info("Starting Gunicorn server...")
    
    port = os.environ.get('PORT', '8000')
    cmd = f"gunicorn core.wsgi:application --preload --max-requests 1000 --max-requests-jitter 100 --workers 2 --threads 2 --timeout 60 --bind 0.0.0.0:{port}"
    
    logger.info(f"Running command: {cmd}")
    return subprocess.Popen(cmd, shell=True)

def start_bot():
    """Start Telegram bot"""
    logger.info("Starting Telegram bot...")
    
    cmd = "python run_bot.py"
    logger.info(f"Running command: {cmd}")
    return subprocess.Popen(cmd, shell=True)

def main():
    """Main function"""
    logger.info("Starting Railway deployment script...")
    
    # Run fixes
    run_fixes()
    
    # Create health check files
    create_health_files()
    
    # Start Gunicorn
    gunicorn_process = start_gunicorn()
    
    # Start bot
    bot_process = start_bot()
    
    # Wait for processes to complete
    logger.info("All processes started, entering monitoring mode")
    
    try:
        while True:
            # Check if processes are still running
            if gunicorn_process.poll() is not None:
                logger.error(f"Gunicorn process exited with code {gunicorn_process.returncode}")
                gunicorn_process = start_gunicorn()
            
            if bot_process.poll() is not None:
                logger.error(f"Bot process exited with code {bot_process.returncode}")
                bot_process = start_bot()
            
            time.sleep(30)
    except KeyboardInterrupt:
        logger.info("Received keyboard interrupt, shutting down")
        gunicorn_process.terminate()
        bot_process.terminate()

if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        logger.error(f"Unhandled error: {e}")
        sys.exit(1)
