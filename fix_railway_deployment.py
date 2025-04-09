#!/usr/bin/env python3
"""
Script to fix Railway deployment issues
"""
import os
import sys
import logging
import django
import subprocess
import time
import signal
import traceback

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Replace the standard StreamHandler with one that has proper encoding
for handler in logger.handlers:
    if isinstance(handler, logging.StreamHandler):
        logger.removeHandler(handler)

# Add new handler with proper encoding
console_handler = logging.StreamHandler(sys.stdout)
console_handler.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))
logger.addHandler(console_handler)

def is_railway_environment():
    """Check if running in Railway environment"""
    return os.environ.get('RAILWAY_ENVIRONMENT') is not None or os.environ.get('RAILWAY_SERVICE_NAME') is not None

def setup_environment_variables():
    """Set up all required environment variables"""
    # Bot settings
    os.environ.setdefault('BOT_TOKEN', "8102516142:AAFTsVXXujHHKoX2KZGqZXBHPBznfgh7kg0")
    os.environ.setdefault('BOT_USERNAME', "chan_parsing_mon_bot")
    
    # API settings
    os.environ.setdefault('API_ID', "19840544")
    os.environ.setdefault('API_HASH', "c839f28bad345082329ec086fca021fa")
    
    # Database settings
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
    
    # For Railway specifically
    if is_railway_environment():
        # PostgreSQL settings for Railway
        os.environ.setdefault('PGHOST', "postgres.railway.internal")
        os.environ.setdefault('PGPORT', "5432")
        os.environ.setdefault('PGUSER', "postgres")
        # Password might already be set by Railway
        if 'PGPASSWORD' not in os.environ:
            logger.warning("PGPASSWORD not set, using default")
            os.environ['PGPASSWORD'] = "postgres"
        os.environ.setdefault('PGDATABASE', "railway")
    
    logger.info("Environment variables set")
    
    # Update .env file for persistence
    try:
        with open('.env', 'a+') as f:
            f.seek(0)
            content = f.read()
            
            env_vars = {
                'BOT_TOKEN': os.environ.get('BOT_TOKEN'),
                'BOT_USERNAME': os.environ.get('BOT_USERNAME'),
                'API_ID': os.environ.get('API_ID'),
                'API_HASH': os.environ.get('API_HASH'),
            }
            
            for key, value in env_vars.items():
                if f"{key}=" not in content and value:
                    f.write(f"\n{key}={value}")
                    logger.info(f"Added {key} to .env file")
    except Exception as e:
        logger.error(f"Error updating .env file: {e}")

def check_and_create_directories():
    """Ensure all required directories exist"""
    directories = [
        'logs',
        'logs/bot',
        'media',
        'staticfiles',
        'data',
        'data/sessions',
        'templates',
        'templates/admin_panel',
    ]
    
    for directory in directories:
        if not os.path.exists(directory):
            os.makedirs(directory, exist_ok=True)
            logger.info(f"Created directory: {directory}")

def apply_django_migrations():
    """Apply Django migrations"""
    try:
        # Initialize Django
        django.setup()
        
        # Run migrations
        from django.core.management import call_command
        
        logger.info("Making migrations...")
        call_command('makemigrations')
        
        logger.info("Applying migrations...")
        call_command('migrate')
        
        logger.info("[OK] Migrations applied successfully")
        return True
    except Exception as e:
        logger.error(f"Error applying migrations: {e}")
        logger.error(traceback.format_exc())
        return False

def check_psycopg2_and_database():
    """Check if psycopg2 is installed and database is accessible"""
    try:
        import psycopg2
        logger.info("[OK] psycopg2 is installed")
        
        # Try connecting to database
        conn = None
        try:
            conn = psycopg2.connect(
                host=os.environ.get('PGHOST', 'localhost'),
                port=os.environ.get('PGPORT', '5432'),
                user=os.environ.get('PGUSER', 'postgres'),
                password=os.environ.get('PGPASSWORD', ''),
                database=os.environ.get('PGDATABASE', 'postgres')
            )
            logger.info("[OK] Successfully connected to PostgreSQL database")
            return True
        except Exception as db_error:
            logger.error(f"Database connection error: {db_error}")
            return False
        finally:
            if conn:
                conn.close()
    except ImportError:
        logger.error("psycopg2 is not installed")
        
        # Try to install psycopg2-binary
        try:
            subprocess.check_call([sys.executable, "-m", "pip", "install", "psycopg2-binary"])
            logger.info("[OK] Installed psycopg2-binary")
            return True
        except Exception as e:
            logger.error(f"Error installing psycopg2-binary: {e}")
            return False

def start_bot():
    """Start the Telegram bot"""
    logger.info("Starting Telegram bot...")
    
    # Check for bot script
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
        # Start bot as a background process
        if sys.platform == 'win32':
            process = subprocess.Popen(
                [sys.executable, bot_script],
                creationflags=subprocess.CREATE_NEW_PROCESS_GROUP | subprocess.DETACHED_PROCESS,
                env=os.environ.copy()
            )
        else:
            process = subprocess.Popen(
                [sys.executable, bot_script],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                env=os.environ.copy()
            )
        
        logger.info(f"[OK] Bot started with PID: {process.pid}")
        
        # Give the bot time to initialize
        time.sleep(2)
        
        return True
    except Exception as e:
        logger.error(f"Error starting bot: {e}")
        return False

def fix_staticfiles():
    """Fix static files collection"""
    try:
        # Initialize Django
        django.setup()
        
        from django.core.management import call_command
        from django.conf import settings
        
        # Ensure STATIC_ROOT is set
        if not hasattr(settings, 'STATIC_ROOT') or not settings.STATIC_ROOT:
            logger.warning("STATIC_ROOT not set, setting to 'staticfiles'")
            settings.STATIC_ROOT = os.path.join(settings.BASE_DIR, 'staticfiles')
        
        # Collect static files
        logger.info("Collecting static files...")
        call_command('collectstatic', '--noinput')
        
        logger.info("[OK] Static files collected")
        return True
    except Exception as e:
        logger.error(f"Error collecting static files: {e}")
        return False

def fix_settings():
    """Fix Django settings problems"""
    try:
        settings_path = 'core/settings.py'
        
        if not os.path.exists(settings_path):
            logger.error(f"Settings file not found at {settings_path}")
            return False
        
        with open(settings_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Ensure TELEGRAM_API_TOKEN is defined
        if 'TELEGRAM_API_TOKEN' not in content:
            insert_point = content.find('# Application definition')
            if insert_point == -1:
                # If not found, insert at the end
                new_content = content + "\n# Telegram API Token\nTELEGRAM_API_TOKEN = os.environ.get('BOT_TOKEN', '8102516142:AAFTsVXXujHHKoX2KZGqZXBHPBznfgh7kg0')\n"
            else:
                # Insert before APPLICATION_DEFINITION
                new_content = content[:insert_point] + "# Telegram API Token\nTELEGRAM_API_TOKEN = os.environ.get('BOT_TOKEN', '8102516142:AAFTsVXXujHHKoX2KZGqZXBHPBznfgh7kg0')\n\n" + content[insert_point:]
            
            with open(settings_path, 'w', encoding='utf-8') as f:
                f.write(new_content)
            
            logger.info("[OK] Added TELEGRAM_API_TOKEN to settings")
        
        # Make sure Django is reloaded
        try:
            import importlib
            from django.conf import settings
            importlib.reload(settings)
            logger.info("[OK] Django settings reloaded")
        except Exception as e:
            logger.error(f"Error reloading Django settings: {e}")
        
        return True
    except Exception as e:
        logger.error(f"Error fixing settings: {e}")
        return False

def test_bot_connection():
    """Test connection to Telegram Bot API"""
    try:
        import requests
        
        bot_token = os.environ.get('BOT_TOKEN', "8102516142:AAFTsVXXujHHKoX2KZGqZXBHPBznfgh7kg0")
        
        # Get bot info from Telegram API
        response = requests.get(f"https://api.telegram.org/bot{bot_token}/getMe")
        
        if response.status_code == 200:
            bot_info = response.json()
            if bot_info.get('ok'):
                bot_username = bot_info['result'].get('username')
                logger.info(f"[OK] Bot connection verified: @{bot_username}")
                return True
            else:
                logger.error(f"Bot verification failed: {bot_info}")
                return False
        else:
            logger.error(f"Bot verification failed with status code {response.status_code}")
            return False
    except Exception as e:
        logger.error(f"Error testing bot connection: {e}")
        return False

def main():
    """Main function to fix Railway deployment"""
    logger.info("=== Starting Railway deployment fix ===")
    
    # Check environment
    is_railway = is_railway_environment()
    logger.info(f"Running in Railway environment: {is_railway}")
    
    # Set up environment variables
    setup_environment_variables()
    
    # Fix directories
    check_and_create_directories()
    
    # Fix Django settings
    fix_settings()
    
    # Fix database connection
    check_psycopg2_and_database()
    
    # Apply migrations
    apply_django_migrations()
    
    # Fix static files
    fix_staticfiles()
    
    # Test bot connection
    test_bot_connection()
    
    # Start bot
    start_bot()
    
    logger.info("=== Railway deployment fix completed ===")

if __name__ == "__main__":
    main()
    sys.exit(0) 