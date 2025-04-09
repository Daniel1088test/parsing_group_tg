#!/usr/bin/env python3
"""
Скрипт для запуску Telegram бота на Railway
"""
import os
import sys
import logging
import time
import traceback
import django
from django.core.management import call_command
import importlib
import subprocess

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger('railway_bot_runner')

# Set up environment variables
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
os.environ.setdefault('BOT_TOKEN', '8102516142:AAFTsVXXujHHKoX2KZGqZXBHPBznfgh7kg0')
os.environ.setdefault('BOT_USERNAME', 'chan_parsing_mon_bot')

def run_migrations():
    """Run database migrations"""
    try:
        logger.info("Running database migrations...")
        # Initialize Django
        django.setup()
        
        # Apply migrations
        call_command('migrate')
        logger.info("Migrations applied successfully")
        return True
    except Exception as e:
        logger.error(f"Error applying migrations: {e}")
        logger.error(traceback.format_exc())
        return False

def check_database():
    """Check database connection"""
    try:
        logger.info("Checking database connection...")
        # Initialize Django if not already initialized
        django.setup()
        
        # Check if we can query something
        from django.db import connection
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
            result = cursor.fetchone()
        
        if result and result[0] == 1:
            logger.info("Database connection successful")
            return True
        else:
            logger.error("Database check query failed")
            return False
    except Exception as e:
        logger.error(f"Database connection error: {e}")
        logger.error(traceback.format_exc())
        return False

def run_bot():
    """Run the bot"""
    try:
        # First try running tg_bot/bot.py directly
        bot_path = os.path.join(os.path.dirname(__file__), 'tg_bot', 'bot.py')
        
        if os.path.exists(bot_path):
            logger.info(f"Starting bot using {bot_path}")
            import importlib.util
            spec = importlib.util.spec_from_file_location("bot", bot_path)
            bot_module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(bot_module)
            
            # Run the main function to start the bot
            if hasattr(bot_module, 'main'):
                logger.info("Launching bot's main function")
                import asyncio
                loop = asyncio.get_event_loop()
                loop.run_until_complete(bot_module.main())
                return True
        
        logger.error(f"Bot module not found at {bot_path}")
        return False
    except Exception as e:
        logger.error(f"Error running bot: {e}")
        logger.error(traceback.format_exc())
        return False

def serve_http():
    """Serve basic HTTP health check"""
    import threading
    import http.server
    import socketserver
    
    class HealthCheckHandler(http.server.SimpleHTTPRequestHandler):
        def do_GET(self):
            if self.path == '/health' or self.path == '/healthz':
                self.send_response(200)
                self.send_header('Content-type', 'text/plain')
                self.end_headers()
                self.wfile.write(b'OK')
            elif self.path == '/metrics':
                self.send_response(200)
                self.send_header('Content-type', 'text/plain')
                self.end_headers()
                self.wfile.write(b'# Bot metrics\nbot_running 1\n')
            else:
                self.send_response(200)
                self.send_header('Content-type', 'text/html')
                self.end_headers()
                self.wfile.write(b'Telegram bot is running')
    
    def run_server():
        port = int(os.environ.get('PORT', 8080))
        with socketserver.TCPServer(("", port), HealthCheckHandler) as httpd:
            logger.info(f"HTTP server started on port {port}")
            try:
                httpd.serve_forever()
            except KeyboardInterrupt:
                httpd.shutdown()
    
    # Start HTTP server in a separate thread
    server_thread = threading.Thread(target=run_server, daemon=True)
    server_thread.start()
    logger.info("Health check HTTP server started in background thread")
    return server_thread

def check_and_install_dependencies():
    """Check for missing dependencies and install them"""
    missing_packages = []
    
    # List of critical packages the bot needs
    required_packages = [
        'qrcode',
        'pillow',
        'aiogram',
        'django',
        'requests',
        'telethon',
        'psycopg2-binary',
        'dj-database-url'
    ]
    
    # Check each package
    for package in required_packages:
        try:
            importlib.import_module(package)
            logger.info(f"Package {package} is already installed")
        except ImportError:
            logger.warning(f"Package {package} is missing")
            missing_packages.append(package)
    
    # Install missing packages
    if missing_packages:
        logger.warning(f"Installing missing packages: {', '.join(missing_packages)}")
        try:
            # Handle special case for pillow (required by qrcode[pil])
            if 'qrcode' in missing_packages and 'pillow' not in missing_packages:
                missing_packages.append('pillow')
            
            # Install packages
            subprocess.check_call([sys.executable, "-m", "pip", "install"] + missing_packages)
            logger.info("All missing packages have been installed")
            return True
        except Exception as e:
            logger.error(f"Error installing packages: {e}")
            return False
    return True

def main():
    """Main function"""
    logger.info("=== Starting Railway Bot Deployment ===")
    
    # Check and install dependencies
    logger.info("Checking and installing dependencies...")
    check_and_install_dependencies()
    
    # Check database
    logger.info("Checking database...")
    db_ok = check_database()
    if not db_ok:
        logger.warning("Database check failed - continuing anyway")
    
    # Run migrations
    logger.info("Running migrations...")
    run_migrations()
    
    # Start health check server
    logger.info("Starting health check server...")
    http_thread = serve_http()
    
    # Run bot
    logger.info("Starting the bot...")
    try:
        run_bot()
    except KeyboardInterrupt:
        logger.info("Bot stopped by user")
    except Exception as e:
        logger.error(f"Bot crashed: {e}")
        logger.error(traceback.format_exc())
        sys.exit(1)
    
    return 0

if __name__ == "__main__":
    sys.exit(main()) 