#!/usr/bin/env python3
"""
Script to start the Telegram bot with all fixes applied
This is the main entry point users should use to run the bot
"""
import os
import sys
import logging
import subprocess
import time
import traceback
from pathlib import Path

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('start_bot.log', encoding='utf-8'),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

# Ensure environment variables are set
os.environ.setdefault('BOT_TOKEN', '8102516142:AAFTsVXXujHHKoX2KZGqZXBHPBznfgh7kg0')
os.environ.setdefault('BOT_USERNAME', 'chan_parsing_mon_bot')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')

def kill_existing_processes():
    """Kill any existing Python processes"""
    try:
        if sys.platform == "win32":
            # Windows
            subprocess.run(["taskkill", "/F", "/IM", "python.exe", "/T"], 
                        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        else:
            # Unix-like
            subprocess.run(["pkill", "-f", "python"], 
                        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        
        # Wait a bit
        time.sleep(2)
        logger.info("Killed existing Python processes")
        return True
    except Exception as e:
        logger.error(f"Error killing processes: {e}")
        return False

def fix_database_config():
    """Fix the database configuration for Railway and local environments"""
    try:
        # Check if running on Railway
        is_railway = os.environ.get('RAILWAY_ENVIRONMENT') is not None or os.environ.get('RAILWAY_SERVICE_NAME') is not None
        
        # Update settings file if it exists
        settings_path = Path('core/settings.py')
        if not settings_path.exists():
            logger.warning(f"Settings file not found at {settings_path}")
            return False
        
        with open(settings_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Add Telegram API Token if missing
        if 'TELEGRAM_API_TOKEN' not in content:
            if '# Application definition' in content:
                content = content.replace(
                    '# Application definition',
                    f'# Telegram API Token\nTELEGRAM_API_TOKEN = os.environ.get("BOT_TOKEN", "{os.environ["BOT_TOKEN"]}")\n\n# Application definition'
                )
            else:
                content += f'\n# Telegram API Token\nTELEGRAM_API_TOKEN = os.environ.get("BOT_TOKEN", "{os.environ["BOT_TOKEN"]}")\n'
            
            logger.info("Added TELEGRAM_API_TOKEN to settings.py")
        
        # Configure database based on environment
        if is_railway:
            # Railway environment with PostgreSQL
            db_config = """
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': os.environ.get('PGDATABASE', 'railway'),
        'USER': os.environ.get('PGUSER', 'postgres'),
        'PASSWORD': os.environ.get('PGPASSWORD', ''),
        'HOST': os.environ.get('PGHOST', 'postgres.railway.internal'),
        'PORT': os.environ.get('PGPORT', '5432'),
    }
}
"""
            logger.info("Configuring for Railway PostgreSQL")
        else:
            # Local environment with SQLite
            db_config = """
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': os.path.join(BASE_DIR, 'db.sqlite3'),
    }
}
"""
            logger.info("Configuring for local SQLite database")
        
        # Update the database configuration
        import re
        if 'DATABASES' in content:
            content = re.sub(
                r'DATABASES\s*=\s*\{[^}]*\}',
                db_config.strip(),
                content
            )
        else:
            content += '\n' + db_config
        
        # Write the updated content
        with open(settings_path, 'w', encoding='utf-8') as f:
            f.write(content)
        
        logger.info("Database configuration updated")
        return True
    except Exception as e:
        logger.error(f"Error fixing database configuration: {e}")
        logger.error(traceback.format_exc())
        return False

def fix_migrations():
    """Fix SQL syntax in migration files"""
    try:
        migrations_dir = Path('admin_panel/migrations')
        if not migrations_dir.exists():
            logger.warning("Migrations directory not found")
            return False
        
        fixed_count = 0
        for migration_file in migrations_dir.glob('*.py'):
            with open(migration_file, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Fix incorrect DO 1 BEGIN syntax in SQL
            if 'DO 1 BEGIN' in content:
                content = content.replace('DO 1 BEGIN', 'DO $$ BEGIN')
                content = content.replace('END 1;', 'END $$;')
                
                with open(migration_file, 'w', encoding='utf-8') as f:
                    f.write(content)
                
                fixed_count += 1
                logger.info(f"Fixed SQL syntax in {migration_file}")
        
        if fixed_count > 0:
            logger.info(f"Fixed SQL syntax in {fixed_count} migration files")
        else:
            logger.info("No SQL syntax issues found in migration files")
        
        return True
    except Exception as e:
        logger.error(f"Error fixing migrations: {e}")
        logger.error(traceback.format_exc())
        return False

def apply_migrations():
    """Apply database migrations"""
    try:
        # Initialize Django
        logger.info("Initializing Django...")
        os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
        try:
            import django
            django.setup()
            
            # Import management commands
            from django.core.management import call_command
            
            # Make migrations
            logger.info("Running makemigrations...")
            call_command('makemigrations')
            
            # Apply migrations
            logger.info("Running migrate...")
            call_command('migrate')
            
            logger.info("Migrations applied successfully")
            return True
        except Exception as e:
            logger.error(f"Error applying migrations: {e}")
            logger.error(traceback.format_exc())
            # Continue anyway, as this might be a first-run issue
            return False
    except Exception as e:
        logger.error(f"Error setting up Django: {e}")
        logger.error(traceback.format_exc())
        return False

def start_bot():
    """Start the bot process"""
    try:
        # First try tg_bot/bot.py directly
        bot_script = 'tg_bot/bot.py'
        if os.path.exists(bot_script):
            logger.info(f"Starting bot using {bot_script}...")
            
            flags = 0
            if sys.platform == "win32":
                flags = subprocess.CREATE_NEW_PROCESS_GROUP | subprocess.DETACHED_PROCESS
                
            process = subprocess.Popen(
                [sys.executable, bot_script],
                creationflags=flags if sys.platform == "win32" else 0,
                start_new_session=True if sys.platform != "win32" else False
            )
            
            logger.info(f"Bot started with PID: {process.pid}")
            return True
        
        # Try alternative scripts
        for script in ['run.py', 'direct_bot_runner.py', 'run_bot.py']:
            if os.path.exists(script):
                logger.info(f"Starting bot using {script}...")
                
                flags = 0
                if sys.platform == "win32":
                    flags = subprocess.CREATE_NEW_PROCESS_GROUP | subprocess.DETACHED_PROCESS
                    
                process = subprocess.Popen(
                    [sys.executable, script],
                    creationflags=flags if sys.platform == "win32" else 0,
                    start_new_session=True if sys.platform != "win32" else False
                )
                
                logger.info(f"Bot started with PID: {process.pid}")
                return True
                
        logger.error("No bot script found to run")
        return False
    except Exception as e:
        logger.error(f"Error starting bot: {e}")
        logger.error(traceback.format_exc())
        return False

def main():
    """Main function"""
    logger.info("=== Starting Telegram Parser Bot ===")
    
    # Kill existing processes
    kill_existing_processes()
    
    # Fix database configuration
    logger.info("Fixing database configuration...")
    fix_database_config()
    
    # Fix migrations SQL
    logger.info("Fixing migration files...")
    fix_migrations()
    
    # Apply migrations
    logger.info("Applying database migrations...")
    apply_migrations()
    
    # Start the bot
    logger.info("Starting bot...")
    success = start_bot()
    
    if success:
        logger.info("=== Bot started successfully ===")
        logger.info("The bot is now running in the background.")
        logger.info("You can access it at https://t.me/chan_parsing_mon_bot")
        logger.info("To stop the bot, close this terminal or press Ctrl+C")
    else:
        logger.error("=== Failed to start bot ===")
        return False
    
    # Keep the script running to make it easy to stop with Ctrl+C
    try:
        while True:
            time.sleep(10)
            sys.stdout.write(".")
            sys.stdout.flush()
    except KeyboardInterrupt:
        logger.info("\nBot stopped by user")
    
    return True

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1) 