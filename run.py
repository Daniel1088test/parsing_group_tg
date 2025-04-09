import os
import asyncio
import signal
import logging
import traceback
import argparse
import django
from multiprocessing import Queue
from datetime import datetime
import sys
import threading
import time

# Configure logging for the entire project
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S',
    filename='app.log',
    filemode='a'
)
logger = logging.getLogger('run_script')

# Global variables to track the processes
processor_process = None
message_queue = None
running = True
bot_proc = None
parser_proc = None

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
try:
    django.setup()
    logger.info("Django successfully initialized")
except Exception as e:
    logger.error(f"Error initializing Django: {e}")
    logger.error(traceback.format_exc())

# Create necessary media directories
try:
    from django.conf import settings
    os.makedirs(settings.MEDIA_ROOT, exist_ok=True)
    os.makedirs(os.path.join(settings.MEDIA_ROOT, 'messages'), exist_ok=True)
    logger.info(f"Ensured media directories exist: {settings.MEDIA_ROOT}/messages")
    
    # Also create static img directory for placeholders
    os.makedirs(os.path.join(settings.STATIC_ROOT, 'img'), exist_ok=True)
except Exception as e:
    logger.error(f"Error creating directories: {e}")
    # Create fallback directories
    os.makedirs('media/messages', exist_ok=True)
    os.makedirs('staticfiles/img', exist_ok=True)

# Fix sessions and restore files if needed
try:
    from django.core.management import call_command
    logger.info("Running fix_sessions command to ensure proper setup...")
    call_command('fix_sessions')
    logger.info("Completed fixing sessions and media files")
    
    # Also run fix_db_schema to ensure database structure is correct
    try:
        call_command('fix_db_schema')
        logger.info("Database schema checked and fixed if needed")
    except Exception as schema_e:
        logger.error(f"Error fixing database schema: {schema_e}")
except Exception as e:
    logger.error(f"Error running fix_sessions command: {e}")
    logger.error(traceback.format_exc())

def signal_handler(sig, frame):
    global running, bot_proc, parser_proc
    logger.info("Received shutdown signal, stopping all processes...")
    running = False
    
    # Stop bot process if running
    if bot_proc:
        try:
            bot_proc.terminate()
            logger.info("Bot process terminated")
        except:
            pass
    
    # Stop parser process if running
    if parser_proc:
        try:
            parser_proc.terminate()
            logger.info("Parser process terminated")
        except:
            pass
    
    sys.exit(0)

# Register signal handlers
signal.signal(signal.SIGINT, signal_handler)
signal.signal(signal.SIGTERM, signal_handler)

def start_bot():
    """Start the Telegram bot in a separate process"""
    global bot_proc
    try:
        import subprocess
        logger.info("Starting Telegram bot process...")
        bot_proc = subprocess.Popen([sys.executable, 'run_bot.py'], 
                                  stdout=subprocess.PIPE, 
                                  stderr=subprocess.STDOUT)
        logger.info(f"Bot process started with PID: {bot_proc.pid}")
        return bot_proc
    except Exception as e:
        logger.error(f"Failed to start bot process: {e}")
        return None

def start_parser():
    """Start the Telegram parser in a separate process"""
    global parser_proc
    try:
        import subprocess
        logger.info("Starting Telegram parser process...")
        parser_proc = subprocess.Popen([sys.executable, 'run_parser.py'], 
                                     stdout=subprocess.PIPE, 
                                     stderr=subprocess.STDOUT)
        logger.info(f"Parser process started with PID: {parser_proc.pid}")
        return parser_proc
    except Exception as e:
        logger.error(f"Failed to start parser process: {e}")
        return None

def monitor_processes():
    """Monitor bot and parser processes and restart them if they crash"""
    global running, bot_proc, parser_proc
    
    while running:
        # Check bot process
        if bot_proc and bot_proc.poll() is not None:
            logger.warning(f"Bot process exited with code {bot_proc.poll()}, restarting...")
            bot_proc = start_bot()
        
        # Check parser process
        if parser_proc and parser_proc.poll() is not None:
            logger.warning(f"Parser process exited with code {parser_proc.poll()}, restarting...")
            parser_proc = start_parser()
        
        # Sleep before checking again
        time.sleep(5)

if __name__ == "__main__":
    logger.info("Starting combined services...")
    
    # Start the bot
    bot_proc = start_bot()
    
    # Start the parser
    parser_proc = start_parser()
    
    # Start the monitoring thread
    monitor_thread = threading.Thread(target=monitor_processes, daemon=True)
    monitor_thread.start()
    
    # Keep the main thread alive
    try:
        while running:
            time.sleep(1)
    except KeyboardInterrupt:
        signal_handler(signal.SIGINT, None)