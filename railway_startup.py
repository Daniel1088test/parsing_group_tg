#!/usr/bin/env python3
"""
Railway Startup Script - Ensures proper database setup and bot startup
This script handles migrations directly without relying on Django's async machinery
"""
import os
import sys
import time
import logging
import subprocess
import traceback
import signal
import io

# Fix for Windows console encoding issues with emoji
if sys.platform == 'win32':
    # Force UTF-8 output encoding when running on Windows
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='backslashreplace')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='backslashreplace')

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('railway_startup.log', encoding='utf-8'),
        logging.StreamHandler(sys.stdout)  # Use stdout instead of stderr for correct encoding
    ]
)
logger = logging.getLogger('railway_startup')

def handle_signal(sig, frame):
    logger.info(f"Received signal {sig}, shutting down...")
    sys.exit(0)

signal.signal(signal.SIGINT, handle_signal)
signal.signal(signal.SIGTERM, handle_signal)

def ensure_environment():
    """Ensure environment variables are set correctly"""
    # Set Django settings
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
    
    # Check for DATABASE_URL for Railway
    database_url = os.environ.get('DATABASE_URL')
    if database_url:
        logger.info(f"Using DATABASE_URL for database connection")
        # Make sure database URL is properly configured in Django settings
        os.environ['USE_POSTGRES'] = 'True'
    else:
        logger.info("No DATABASE_URL found, will use SQLite database")
    
    # Get bot token
    token = os.environ.get('BOT_TOKEN')
    if not token and os.path.exists('bot_token.env'):
        try:
            with open('bot_token.env', 'r') as f:
                content = f.read().strip()
                if content.startswith('BOT_TOKEN='):
                    token = content.split('=', 1)[1].strip()
                    os.environ['BOT_TOKEN'] = token
                    logger.info(f"Loaded BOT_TOKEN from bot_token.env")
        except Exception as e:
            logger.error(f"Error reading bot_token.env: {e}")
    
    # Fallback to hardcoded token if still not set
    if not token:
        hardcoded_token = "7923260865:AAGYew9JnOJV6hz0LGeRCb1kS6AejHoX61g"
        os.environ['BOT_TOKEN'] = hardcoded_token
        logger.warning(f"Using hardcoded token")
        
        # Save it to file for consistency
        with open('bot_token.env', 'w') as f:
            f.write(f"BOT_TOKEN={hardcoded_token}")
    
    return True

def run_command(cmd, capture_output=True):
    """Run a shell command and return the output"""
    try:
        logger.info(f"Running command: {cmd}")
        if capture_output:
            result = subprocess.run(
                cmd, 
                shell=True, 
                stdout=subprocess.PIPE, 
                stderr=subprocess.PIPE,
                text=True,
                check=False
            )
            if result.returncode != 0:
                logger.warning(f"Command exited with code {result.returncode}")
                logger.warning(f"STDERR: {result.stderr}")
            else:
                logger.info(f"Command completed successfully")
            return result.stdout
        else:
            # Just run without capturing output
            subprocess.run(cmd, shell=True, check=False)
            return None
    except Exception as e:
        logger.error(f"Error running command: {e}")
        return None

def create_health_checks():
    """Create health check files"""
    for file in ['health.txt', 'healthz.txt', 'health.html', 'healthz.html']:
        try:
            with open(file, 'w') as f:
                f.write('ok')
            logger.info(f"Created health check file: {file}")
        except Exception as e:
            logger.error(f"Error creating health check file {file}: {e}")

def ensure_directories():
    """Create necessary directories"""
    directories = [
        'logs/bot',
        'media/messages',
        'staticfiles/media',
        'data/sessions'
    ]
    for directory in directories:
        try:
            os.makedirs(directory, exist_ok=True)
            logger.info(f"Created directory: {directory}")
        except Exception as e:
            logger.error(f"Error creating directory {directory}: {e}")

def fix_database():
    """Fix database directly using SQL if needed"""
    try:
        import django
        django.setup()
        
        from django.db import connection
        
        with connection.cursor() as cursor:
            # Verify connection
            cursor.execute("SELECT 1")
            logger.info("Database connection verified")
            
            # Check if BotSettings table exists
            cursor.execute("""
                SELECT EXISTS (
                    SELECT FROM information_schema.tables 
                    WHERE table_name='admin_panel_botsettings'
                ) AS table_exists
            """)
            table_exists = cursor.fetchone()[0]
            
            if not table_exists:
                logger.info("Creating BotSettings table")
                cursor.execute("""
                    CREATE TABLE admin_panel_botsettings (
                        id SERIAL PRIMARY KEY,
                        bot_token VARCHAR(255) NOT NULL,
                        bot_username VARCHAR(255) NULL,
                        bot_name VARCHAR(255) NULL,
                        welcome_message TEXT NULL,
                        auth_guide_text TEXT NULL,
                        menu_style VARCHAR(50) NULL,
                        default_api_id INTEGER NULL,
                        default_api_hash VARCHAR(255) NULL,
                        polling_interval INTEGER NULL,
                        max_messages_per_channel INTEGER NULL,
                        created_at TIMESTAMP NULL,
                        updated_at TIMESTAMP NULL
                    )
                """)
            
            # Check if we have a BotSettings record
            cursor.execute("SELECT COUNT(*) FROM admin_panel_botsettings")
            count = cursor.fetchone()[0]
            
            # Get token from environment
            token = os.environ.get('BOT_TOKEN')
            
            if count == 0 and token:
                logger.info("Creating default BotSettings record")
                cursor.execute("""
                    INSERT INTO admin_panel_botsettings 
                    (bot_token, bot_username, bot_name, menu_style, default_api_id, 
                     polling_interval, max_messages_per_channel)
                    VALUES (%s, %s, %s, %s, %s, %s, %s)
                """, [
                    token, 'Channels_hunt_bot', 'Channel Parser Bot', 'default', 
                    2496, 30, 10
                ])
            elif token:
                logger.info("Updating existing BotSettings record")
                cursor.execute("""
                    UPDATE admin_panel_botsettings
                    SET bot_token = %s, bot_username = %s
                    WHERE id = (SELECT MIN(id) FROM admin_panel_botsettings)
                """, [token, 'Channels_hunt_bot'])
            
            # Commit changes
            connection.commit()
            logger.info("Database fixes committed")
        
        return True
    except Exception as e:
        logger.error(f"Error fixing database: {e}")
        logger.error(traceback.format_exc())
        return False

def apply_migrations():
    """Apply Django migrations directly"""
    try:
        import django
        django.setup()
        
        from django.core.management import call_command
        
        # First just try standard migrate
        try:
            logger.info("Applying migrations with standard approach")
            call_command('migrate', verbosity=1, interactive=False)
            logger.info("Standard migrations completed")
            return True
        except Exception as e:
            logger.error(f"Error with standard migrations: {e}")
            
            # Try alternative approach
            try:
                logger.info("Trying migrations app by app")
                for app in ['admin', 'auth', 'contenttypes', 'sessions', 'admin_panel', 'tg_bot']:
                    try:
                        logger.info(f"Migrating {app}")
                        call_command('migrate', app, verbosity=1, interactive=False)
                    except Exception as app_error:
                        logger.error(f"Error migrating {app}: {app_error}")
                
                logger.info("App-by-app migrations completed")
                return True
            except Exception as alt_error:
                logger.error(f"Error with alternative migrations: {alt_error}")
                return False
    except Exception as e:
        logger.error(f"Error in apply_migrations: {e}")
        logger.error(traceback.format_exc())
        return False

def run_bot_process():
    """Start the bot process directly"""
    try:
        # Create log directory
        os.makedirs('logs/bot', exist_ok=True)
        
        # Start the bot as a subprocess
        bot_cmd = f"{sys.executable} direct_start_bot.py"
        logger.info(f"Starting bot with command: {bot_cmd}")
        
        proc = subprocess.Popen(
            bot_cmd,
            shell=True,
            stdout=open('logs/bot/direct_start.log', 'w'),
            stderr=subprocess.STDOUT
        )
        
        logger.info(f"Bot process started with PID: {proc.pid}")
        
        # Write PID to file
        with open('railway_bot.pid', 'w') as f:
            f.write(str(proc.pid))
        
        return proc
    except Exception as e:
        logger.error(f"Error starting bot: {e}")
        logger.error(traceback.format_exc())
        return None

def start_django_server():
    """Start the Django server in the foreground"""
    try:
        port = os.environ.get('PORT', 8080)
        cmd = f"{sys.executable} manage.py runserver 0.0.0.0:{port}"
        logger.info(f"Starting Django server with command: {cmd}")
        
        # Run in the foreground to keep the Railway process alive
        os.execvp('python', ['python', 'manage.py', 'runserver', f'0.0.0.0:{port}'])
    except Exception as e:
        logger.error(f"Error starting Django server: {e}")
        logger.error(traceback.format_exc())
        return None

def main():
    """Main function to orchestrate the startup process"""
    logger.info("=== Railway Startup Script ===")
    
    # Set up environment
    ensure_environment()
    
    # Create health checks
    create_health_checks()
    
    # Ensure directories
    ensure_directories()
    
    # Fix database directly
    if not fix_database():
        logger.warning("Database fix encountered issues, but continuing...")
    
    # Apply migrations
    if not apply_migrations():
        logger.warning("Migrations encountered issues, but continuing...")
    
    # Execute the emergency fix script for good measure
    try:
        run_command("chmod +x emergency_fix.sh")
        run_command("./emergency_fix.sh", capture_output=False)
    except Exception as e:
        logger.error(f"Error running emergency fix script: {e}")
    
    # Start the bot
    bot_process = run_bot_process()
    if not bot_process:
        logger.error("Failed to start bot process")
    
    # Give the bot a moment to start
    time.sleep(5)
    
    # Check if the bot is still running
    if bot_process and bot_process.poll() is None:
        logger.info("Bot process is still running after 5 seconds")
    else:
        logger.error("Bot process has already exited")
    
    # Start the Django server
    logger.info("Starting Django server...")
    start_django_server()

if __name__ == "__main__":
    main() 