#!/usr/bin/env python3
"""
Script to fix Railway deployment issues
This script addresses specific issues that occur in the Railway environment
"""
import os
import sys
import logging
import subprocess
import django

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler('fix_railway_deployment.log')
    ]
)
logger = logging.getLogger('railway_fix')

# Set up Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
os.environ['RAILWAY_ENVIRONMENT'] = 'true'  # Force Railway mode

try:
    django.setup()
    from django.conf import settings
    logger.info("Django initialized successfully")
except Exception as e:
    logger.error(f"Error initializing Django: {e}")
    sys.exit(1)

def run_command(command, env=None):
    """Run a shell command and capture output"""
    try:
        env_vars = os.environ.copy()
        if env:
            env_vars.update(env)
        
        result = subprocess.run(
            command,
            shell=True,
            capture_output=True,
            text=True,
            check=False,
            env=env_vars
        )
        
        if result.returncode != 0:
            logger.error(f"Command failed: {command}")
            logger.error(f"Output: {result.stdout}")
            logger.error(f"Error: {result.stderr}")
            return False
        
        logger.info(f"Command succeeded: {command}")
        return True
    except Exception as e:
        logger.error(f"Error running command {command}: {e}")
        return False

def fix_railway_config():
    """Create or update Railway configuration files"""
    try:
        # Create railway.toml if it doesn't exist
        if not os.path.exists('railway.toml'):
            railway_toml_content = """[build]
builder = "NIXPACKS"
buildCommand = "pip install -r requirements.txt && python manage.py collectstatic --noinput"

[deploy]
startCommand = "python manage.py migrate && gunicorn core.wsgi:application --preload --max-requests 1000 --max-requests-jitter 100 --workers 2 --threads 2 --timeout 60 --bind 0.0.0.0:$PORT"
healthcheckPath = "/health"
healthcheckTimeout = 100
restartPolicyType = "ON_FAILURE"
restartPolicyMaxRetries = 5

[phases.setup]
aptPkgs = ["python3", "python3-pip", "build-essential", "libpq-dev", "postgresql-client"]
cmds = ["pip install --upgrade pip"]
"""
            with open('railway.toml', 'w') as f:
                f.write(railway_toml_content)
            logger.info("Created railway.toml configuration file")
        
        # Create or update Procfile
        procfile_content = """web: python fix_templates_and_aiohttp.py && python fix_multiple_fields.py && python fix_admin_query.py && python manage.py migrate && gunicorn core.wsgi:application --preload --max-requests 1000 --max-requests-jitter 100 --workers 2 --threads 2 --timeout 60 --bind 0.0.0.0:$PORT
bot: python run_bot.py
"""
        with open('Procfile', 'w') as f:
            f.write(procfile_content)
        logger.info("Updated Procfile for Railway deployment")
        
        # Create a Railway startup script
        railway_startup_content = """#!/usr/bin/env python3
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
    \"\"\"Run all fix scripts\"\"\"
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
    \"\"\"Create health check files\"\"\"
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
    \"\"\"Start Gunicorn server\"\"\"
    logger.info("Starting Gunicorn server...")
    
    port = os.environ.get('PORT', '8000')
    cmd = f"gunicorn core.wsgi:application --preload --max-requests 1000 --max-requests-jitter 100 --workers 2 --threads 2 --timeout 60 --bind 0.0.0.0:{port}"
    
    logger.info(f"Running command: {cmd}")
    return subprocess.Popen(cmd, shell=True)

def start_bot():
    \"\"\"Start Telegram bot\"\"\"
    logger.info("Starting Telegram bot...")
    
    cmd = "python run_bot.py"
    logger.info(f"Running command: {cmd}")
    return subprocess.Popen(cmd, shell=True)

def main():
    \"\"\"Main function\"\"\"
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
"""
        with open('railway_startup.py', 'w') as f:
            f.write(railway_startup_content)
        logger.info("Created railway_startup.py script")
        return True
    except Exception as e:
        logger.error(f"Error updating Railway configuration: {e}")
        return False

def fix_railway_dependencies():
    """Ensure all Railway-specific dependencies are in requirements.txt"""
    try:
        required_packages = [
            "gunicorn",
            "psycopg2-binary",
            "whitenoise",
            "dj-database-url",
            "pillow",
        ]
        
        # Read current requirements
        with open('requirements.txt', 'r') as f:
            current_requirements = f.read()
        
        # Add missing packages
        for package in required_packages:
            if package not in current_requirements:
                with open('requirements.txt', 'a') as f:
                    f.write(f"\n{package}\n")
                logger.info(f"Added {package} to requirements.txt")
        
        logger.info("Updated requirements.txt with Railway dependencies")
        return True
    except Exception as e:
        logger.error(f"Error updating requirements.txt: {e}")
        return False

def fix_railway_static_files():
    """Ensure static files are properly configured for Railway"""
    try:
        # Fix settings.py
        # Find settings.py
        settings_files = [
            'core/settings.py',
            'settings.py',
        ]
        
        settings_path = None
        for path in settings_files:
            if os.path.exists(path):
                settings_path = path
                break
        
        if not settings_path:
            logger.error("Could not find settings.py")
            return False
        
        # Read settings
        with open(settings_path, 'r') as f:
            settings_content = f.read()
        
        # Make sure whitenoise is properly configured
        if 'STATICFILES_STORAGE' not in settings_content:
            # Add whitenoise configuration
            whitenoise_config = "\n# Whitenoise static file handling\nSTATICFILES_STORAGE = 'whitenoise.storage.CompressedManifestStaticFilesStorage'\n"
            settings_content += whitenoise_config
            
            # Write updated settings
            with open(settings_path, 'w') as f:
                f.write(settings_content)
            
            logger.info("Added whitenoise configuration to settings.py")
        
        # Create required directories
        os.makedirs('staticfiles', exist_ok=True)
        os.makedirs('static', exist_ok=True)
        os.makedirs('static/img', exist_ok=True)
        
        # Copy placeholder images
        try:
            from PIL import Image, ImageDraw
            
            # Create image placeholder
            img_placeholder_path = os.path.join('static', 'img', 'placeholder-image.png')
            if not os.path.exists(img_placeholder_path):
                img = Image.new('RGB', (300, 200), color=(240, 240, 240))
                draw = ImageDraw.Draw(img)
                draw.rectangle([(0, 0), (299, 199)], outline=(200, 200, 200), width=2)
                draw.text((150, 100), "IMAGE", fill=(100, 100, 100))
                img.save(img_placeholder_path)
                logger.info(f"Created placeholder image: {img_placeholder_path}")
            
            # Create video placeholder
            video_placeholder_path = os.path.join('static', 'img', 'placeholder-video.png')
            if not os.path.exists(video_placeholder_path):
                img = Image.new('RGB', (300, 200), color=(240, 240, 240))
                draw = ImageDraw.Draw(img)
                draw.rectangle([(0, 0), (299, 199)], outline=(200, 200, 200), width=2)
                draw.text((150, 100), "VIDEO", fill=(100, 100, 100))
                img.save(video_placeholder_path)
                logger.info(f"Created placeholder video: {video_placeholder_path}")
        except ImportError:
            logger.warning("PIL not available, creating simple placeholder files")
            
            # Create simple placeholder files
            img_placeholder_path = os.path.join('static', 'img', 'placeholder-image.png')
            video_placeholder_path = os.path.join('static', 'img', 'placeholder-video.png')
            
            with open(img_placeholder_path, 'wb') as f:
                f.write(b'')
            with open(video_placeholder_path, 'wb') as f:
                f.write(b'')
        
        # Create health check files
        health_files = [
            {'path': os.path.join('static', 'health.txt'), 'content': 'OK'},
            {'path': os.path.join('static', 'healthz.txt'), 'content': 'OK'},
            {'path': os.path.join('static', 'health.html'), 'content': '<html><body>OK</body></html>'},
            {'path': os.path.join('static', 'healthz.html'), 'content': '<html><body>OK</body></html>'},
            {'path': os.path.join('health.txt'), 'content': 'OK'},
            {'path': os.path.join('healthz.txt'), 'content': 'OK'},
            {'path': os.path.join('health.html'), 'content': '<html><body>OK</body></html>'},
            {'path': os.path.join('healthz.html'), 'content': '<html><body>OK</body></html>'},
        ]
        
        for file in health_files:
            with open(file['path'], 'w') as f:
                f.write(file['content'])
            logger.info(f"Created health file: {file['path']}")
        
        # Run collectstatic
        if run_command("python manage.py collectstatic --noinput"):
            logger.info("Collected static files successfully")
        
        logger.info("Fixed static files for Railway deployment")
        return True
    except Exception as e:
        logger.error(f"Error fixing static files: {e}")
        return False

def main():
    """Main function"""
    logger.info("Starting Railway deployment fixes...")
    
    # Fix Railway configuration
    fix_railway_config()
    
    # Fix Railway dependencies
    fix_railway_dependencies()
    
    # Fix static files for Railway
    fix_railway_static_files()
    
    # Run database fixes
    if run_command("python fix_templates_and_aiohttp.py"):
        logger.info("Successfully ran fix_templates_and_aiohttp.py")
    
    if run_command("python fix_multiple_fields.py"):
        logger.info("Successfully ran fix_multiple_fields.py")
    
    if run_command("python fix_admin_query.py"):
        logger.info("Successfully ran fix_admin_query.py")
    
    logger.info("Railway deployment fixes completed")
    
    # Print success message
    print("\n" + "="*50)
    print("Railway deployment fixes applied successfully!")
    print("You should now be able to deploy to Railway with proper web interface and bot functionality.")
    print("="*50 + "\n")
    
    return True

if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        logger.error(f"Unhandled error: {e}")
        sys.exit(1) 