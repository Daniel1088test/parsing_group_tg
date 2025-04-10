#!/usr/bin/env python3
"""
Master script to run the application with all fixes and checks
"""
import os
import sys
import subprocess
import time
import logging
import importlib.util
import traceback

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(stream=open(os.devnull, 'w')),  # Dummy handler to avoid encoding issues
        logging.FileHandler('app_runner.log', encoding='utf-8')
    ]
)
logger = logging.getLogger("app_runner")

# Add console handler with proper encoding
console_handler = logging.StreamHandler(sys.stdout)
console_handler.setLevel(logging.INFO)
console_handler.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))
logger.addHandler(console_handler)

def check_and_run_fix(script_name):
    """Check if a fix script exists and run it if it does"""
    if os.path.exists(script_name):
        logger.info(f"Running fix script: {script_name}")
        try:
            # Run the script using Python interpreter
            result = subprocess.run([sys.executable, script_name], capture_output=True, text=True)
            if result.returncode == 0:
                logger.info(f"[OK] Fix script {script_name} completed successfully")
            else:
                logger.error(f"Fix script {script_name} failed with error: {result.stderr}")
        except Exception as e:
            logger.error(f"Error running fix script {script_name}: {e}")
    else:
        logger.info(f"Fix script {script_name} not found, skipping")

def setup_environment():
    """Setup environment variables"""
    # Essential environment variables
    env_vars = {
        'BOT_TOKEN': '8102516142:AAFTsVXXujHHKoX2KZGqZXBHPBznfgh7kg0',
        'BOT_USERNAME': 'chan_parsing_mon_bot',
        'API_ID': '19840544',
        'API_HASH': 'c839f28bad345082329ec086fca021fa',
        'DJANGO_SETTINGS_MODULE': 'core.settings'
    }
    
    # Set default environment variables if not already set
    for key, value in env_vars.items():
        if key not in os.environ or not os.environ[key]:
            os.environ[key] = value
            logger.info(f"Set environment variable: {key}")
            
    # Check if we're in a Railway environment
    if 'RAILWAY_ENVIRONMENT' in os.environ or 'RAILWAY_SERVICE_NAME' in os.environ:
        logger.info("Running in Railway environment")
        # Additional Railway-specific environment variables
        railway_vars = {
            'PGHOST': 'postgres.railway.internal',
            'PGPORT': '5432',
            'PGUSER': 'postgres',
            'PGDATABASE': 'railway'
        }
        
        for key, value in railway_vars.items():
            if key not in os.environ or not os.environ[key]:
                os.environ[key] = value
                logger.info(f"Set Railway environment variable: {key}")

def check_directories():
    """Check and create necessary directories"""
    directories = [
        'staticfiles',
        'media',
        'logs/bot',
        'data/sessions',
        'templates',
        'templates/admin_panel'
    ]
    
    for directory in directories:
        if not os.path.exists(directory):
            os.makedirs(directory, exist_ok=True)
            logger.info(f"Created directory: {directory}")
    
    return True

def fix_django_settings():
    """Fix Django settings"""
    try:
        # Check if TELEGRAM_API_TOKEN is in settings
        settings_path = os.path.join('core', 'settings.py')
        
        if not os.path.exists(settings_path):
            logger.warning(f"Settings file not found at {settings_path}")
            return False
            
        with open(settings_path, 'r', encoding='utf-8') as f:
            content = f.read()
            
        if 'TELEGRAM_API_TOKEN' not in content:
            # Add TELEGRAM_API_TOKEN to settings
            logger.info("Adding TELEGRAM_API_TOKEN to Django settings")
            token_line = "\n# Telegram API Token\nTELEGRAM_API_TOKEN = os.environ.get('BOT_TOKEN', '8102516142:AAFTsVXXujHHKoX2KZGqZXBHPBznfgh7kg0')\n"
            
            # Find a good insertion point
            if '# Application definition' in content:
                new_content = content.replace('# Application definition', token_line + '# Application definition')
            else:
                new_content = content + token_line
                
            with open(settings_path, 'w', encoding='utf-8') as f:
                f.write(new_content)
                
            logger.info("✓ TELEGRAM_API_TOKEN added to Django settings")
            
        # Initialize Django to check settings
        os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
        try:
            import django
            django.setup()
            from django.conf import settings
            if hasattr(settings, 'TELEGRAM_API_TOKEN'):
                logger.info(f"✓ TELEGRAM_API_TOKEN successfully loaded in Django: {settings.TELEGRAM_API_TOKEN}")
            else:
                logger.error("TELEGRAM_API_TOKEN not found in Django settings")
                return False
        except Exception as e:
            logger.error(f"Error initializing Django: {e}")
            logger.error(traceback.format_exc())
            return False
            
        return True
    except Exception as e:
        logger.error(f"Error fixing Django settings: {e}")
        return False

def start_bot():
    """Start the Telegram bot"""
    logger.info("Starting Telegram bot...")
    
    # Check for bot runner scripts
    bot_scripts = [
        'direct_bot_runner.py',
        'run_bot.py',
        'tg_bot/bot.py'
    ]
    
    bot_script = None
    for script in bot_scripts:
        if os.path.exists(script):
            bot_script = script
            break
    
    if not bot_script:
        logger.error("No bot script found")
        return False
    
    try:
        # Start the bot process
        if sys.platform == 'win32':
            # Windows-specific process creation
            process = subprocess.Popen(
                [sys.executable, bot_script],
                creationflags=subprocess.CREATE_NEW_PROCESS_GROUP | subprocess.DETACHED_PROCESS,
                env=os.environ.copy()
            )
        else:
            # Unix process creation
            process = subprocess.Popen(
                [sys.executable, bot_script],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                env=os.environ.copy(),
                start_new_session=True
            )
        
        logger.info(f"[OK] Bot started with PID: {process.pid}")
        
        # Give the bot some time to initialize
        time.sleep(2)
        
        return True
    except Exception as e:
        logger.error(f"Error starting bot: {e}")
        return False

def start_django():
    """Start the Django application"""
    logger.info("Starting Django application...")
    
    # Default to port 8080
    port = os.environ.get('PORT', '8080')
    
    try:
        # Check if gunicorn is available
        gunicorn_spec = importlib.util.find_spec('gunicorn')
        
        if gunicorn_spec:
            # Use gunicorn for production
            cmd = [
                'gunicorn',
                'core.wsgi:application',
                f'--bind=0.0.0.0:{port}',
                '--workers=3',
                '--timeout=120'
            ]
            logger.info(f"Starting Django with gunicorn on port {port}")
        else:
            # Use Django's development server
            cmd = [
                sys.executable,
                'manage.py',
                'runserver',
                f'0.0.0.0:{port}'
            ]
            logger.info(f"Starting Django development server on port {port}")
        
        # Start the Django process
        process = subprocess.Popen(
            cmd,
            env=os.environ.copy()
        )
        
        logger.info(f"[OK] Django started with PID: {process.pid}")
        
        return True
    except Exception as e:
        logger.error(f"Error starting Django: {e}")
        return False

def start_parser():
    """Start the parser process"""
    logger.info("Starting parser...")
    
    # Check for parser script
    parser_scripts = [
        'run_parser.py',
        'parser/main.py'
    ]
    
    parser_script = None
    for script in parser_scripts:
        if os.path.exists(script):
            parser_script = script
            break
    
    if not parser_script:
        logger.warning("No parser script found, skipping parser start")
        return False
    
    try:
        # Start the parser process
        if sys.platform == 'win32':
            # Windows-specific process creation
            process = subprocess.Popen(
                [sys.executable, parser_script],
                creationflags=subprocess.CREATE_NEW_PROCESS_GROUP | subprocess.DETACHED_PROCESS,
                env=os.environ.copy()
            )
        else:
            # Unix process creation
            process = subprocess.Popen(
                [sys.executable, parser_script],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                env=os.environ.copy(),
                start_new_session=True
            )
        
        logger.info(f"[OK] Parser started with PID: {process.pid}")
        
        return True
    except Exception as e:
        logger.error(f"Error starting parser: {e}")
        return False

def main():
    """Main function to run the application with all checks and fixes"""
    logger.info("=== Starting application runner ===")
    
    # Setup environment variables
    setup_environment()
    
    # Check and create directories
    check_directories()
    
    # Run fix scripts
    fix_scripts = [
        'fix_templates_and_aiohttp.py',
        'fix_railway_deployment.py',
        'dockerfile_fix.py'
    ]
    
    for script in fix_scripts:
        check_and_run_fix(script)
    
    # Fix Django settings
    fix_django_settings()
    
    # Start components
    start_bot()
    start_parser()
    start_django()
    
    logger.info("=== Application started successfully ===")
    logger.info("Press Ctrl+C to stop")
    
    # Keep the script running
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        logger.info("Stopping application...")
    except Exception as e:
        logger.error(f"Error in main loop: {e}")
    
    logger.info("Application stopped")

if __name__ == "__main__":
    main()