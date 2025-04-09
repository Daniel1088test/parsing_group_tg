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
import subprocess
from asgiref.sync import sync_to_async  # Add import for async Django support

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

# Load bot token from environment or file
def ensure_bot_token():
    if 'BOT_TOKEN' not in os.environ or not os.environ['BOT_TOKEN']:
        # Try to get token from bot_token.env file
        if os.path.exists('bot_token.env'):
            try:
                with open('bot_token.env', 'r') as f:
                    content = f.read().strip()
                    if content.startswith('BOT_TOKEN='):
                        token = content.split('=', 1)[1].strip()
                        os.environ['BOT_TOKEN'] = token
                        logger.info(f"Loaded BOT_TOKEN from bot_token.env file")
                        return True
            except Exception as e:
                logger.error(f"Error reading bot_token.env: {e}")
                
        # Try to get token from config.py
        try:
            from tg_bot.config import TOKEN_BOT
            if TOKEN_BOT:
                os.environ['BOT_TOKEN'] = TOKEN_BOT
                logger.info(f"Loaded BOT_TOKEN from config.py")
                return True
        except Exception as e:
            logger.error(f"Error loading token from config.py: {e}")
            
        # Try hardcoded token as last resort in Railway environment
        if os.environ.get('RAILWAY_SERVICE_NAME'):
            hardcoded_token = "7923260865:AAGYew9JnOJV6hz0LGeRCb1kS6AejHoX61g"
            os.environ['BOT_TOKEN'] = hardcoded_token
            logger.info(f"Using hardcoded token in Railway environment")
            
            # Try to save it to files to ensure consistency
            try:
                with open('bot_token.env', 'w') as f:
                    f.write(f"BOT_TOKEN={hardcoded_token}")
                logger.info("Saved hardcoded token to bot_token.env")
            except Exception as e:
                logger.error(f"Error saving token to bot_token.env: {e}")
            
            return True
            
        # Token not found
        logger.error("BOT_TOKEN not set and couldn't be loaded from files!")
        return False
    
    return True

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
    
    # First ensure we have a bot token
    if not ensure_bot_token():
        logger.error("Cannot start bot without a valid BOT_TOKEN")
        return None
    
    # Print the token for debugging (first 10 chars + last 4)
    token = os.environ.get('BOT_TOKEN', '')
    if token:
        safe_token = token[:10] + "..." + token[-4:] if len(token) > 14 else "invalid_format"
        logger.info(f"Using token: {safe_token}")
    
    try:
        import subprocess
        logger.info("Starting Telegram bot process...")
        
        # Kill any previous instance first
        if bot_proc and bot_proc.poll() is None:
            try:
                bot_proc.terminate()
                logger.info("Terminated previous bot process")
                time.sleep(1)
            except:
                pass
        
        # Try several methods to start the bot
        methods = [
            # Method 1: Direct module run
            [sys.executable, 'run_bot.py'],
            
            # Method 2: Direct bot script
            [sys.executable, 'tg_bot/bot.py'],
            
            # Method 3: Import-based execution
            [sys.executable, '-c', 'import os; os.environ.setdefault("DJANGO_SETTINGS_MODULE", "core.settings"); import django; django.setup(); import asyncio; from tg_bot.bot import main; asyncio.run(main())']
        ]
        
        # Prepare environment with explicit BOT_TOKEN
        env = os.environ.copy()
        
        # Try each method until one works
        for i, method in enumerate(methods):
            logger.info(f"Trying bot start method {i+1}")
            
            # Create log directory if it doesn't exist
            os.makedirs('logs/bot', exist_ok=True)
            
            # Start process with output to log file
            log_file = f'logs/bot/bot_method_{i+1}.log'
            with open(log_file, 'w') as f:
                bot_proc = subprocess.Popen(
                    method,
                    stdout=f,
                    stderr=subprocess.STDOUT,
                    env=env  # Ensure environment variables are passed
                )
            
            # Give it a moment to initialize
            time.sleep(5)
            
            # Check if process is still running
            if bot_proc and bot_proc.poll() is None:
                logger.info(f"Bot process started successfully with PID: {bot_proc.pid} (method {i+1})")
                # Write PID to file for external monitoring
                with open('bot.pid', 'w') as f:
                    f.write(str(bot_proc.pid))
                return bot_proc
            else:
                logger.warning(f"Bot start method {i+1} failed, trying next method")
                # Print the log for debugging
                try:
                    with open(log_file, 'r') as f:
                        log_content = f.read()
                        logger.warning(f"Bot startup log for method {i+1}:\n{log_content}")
                except Exception as e:
                    logger.error(f"Error reading bot log: {e}")
        
        logger.error("All bot start methods failed")
        
        # Special handling for Railway - try a direct approach
        if os.environ.get('RAILWAY_SERVICE_NAME'):
            logger.info("Running in Railway environment, trying direct bot execution")
            with open('logs/bot/bot_direct.log', 'w') as f:
                direct_proc = subprocess.Popen(
                    [sys.executable, '-m', 'tg_bot.bot'],
                    stdout=f,
                    stderr=subprocess.STDOUT,
                    env=env
                )
            
            time.sleep(5)
            if direct_proc and direct_proc.poll() is None:
                logger.info(f"Direct bot start successful with PID: {direct_proc.pid}")
                bot_proc = direct_proc
                with open('bot.pid', 'w') as f:
                    f.write(str(direct_proc.pid))
                return direct_proc
            else:
                logger.error("Direct bot start failed too")
        
        return None
    except Exception as e:
        logger.error(f"Failed to start bot process: {e}")
        logger.error(traceback.format_exc())
        return None

def start_parser():
    """Start the Telegram parser in a separate process"""
    global parser_proc
    try:
        import subprocess
        logger.info("Starting Telegram parser process...")
        
        # Kill any previous instance first
        if parser_proc and parser_proc.poll() is None:
            try:
                parser_proc.terminate()
                logger.info("Terminated previous parser process")
                time.sleep(1)
            except:
                pass
        
        # Prepare environment with explicit variables
        env = os.environ.copy()
        
        # Create log directory if it doesn't exist
        os.makedirs('logs/bot', exist_ok=True)
        
        # Start with output to log file
        with open('logs/bot/parser.log', 'w') as f:
            parser_proc = subprocess.Popen(
                [sys.executable, 'run_parser.py'],
                stdout=f,
                stderr=subprocess.STDOUT,
                env=env  # Ensure environment variables are passed
            )
        
        # Give it a moment to initialize
        time.sleep(3)
        
        # Check if process is still running
        if parser_proc.poll() is None:
            logger.info(f"Parser process started with PID: {parser_proc.pid}")
            # Write PID to file for external monitoring
            with open('parser.pid', 'w') as f:
                f.write(str(parser_proc.pid))
            return parser_proc
        else:
            logger.error("Parser process failed to start")
            # Print the log for debugging
            try:
                with open('logs/bot/parser.log', 'r') as f:
                    log_content = f.read()
                    logger.error(f"Parser startup log:\n{log_content}")
            except Exception as e:
                logger.error(f"Error reading parser log: {e}")
            return None
    except Exception as e:
        logger.error(f"Failed to start parser process: {e}")
        logger.error(traceback.format_exc())
        return None

def monitor_processes():
    """Monitor bot and parser processes and restart them if they crash"""
    global running, bot_proc, parser_proc
    
    # Debug the environment variables
    logger.info(f"BOT_TOKEN: {'Set' if 'BOT_TOKEN' in os.environ and os.environ['BOT_TOKEN'] else 'Not set'}")
    logger.info(f"DATABASE_URL: {'Set' if 'DATABASE_URL' in os.environ and os.environ['DATABASE_URL'] else 'Not set'}")
    
    # Time tracking for restart cooldown
    last_bot_restart = 0
    last_parser_restart = 0
    restart_cooldown = 60  # Seconds to wait before restarting a crashed process
    
    while running:
        current_time = time.time()
        
        # Check bot process
        if bot_proc and bot_proc.poll() is not None:
            if current_time - last_bot_restart > restart_cooldown:
                logger.warning(f"Bot process exited with code {bot_proc.poll()}, restarting...")
                bot_proc = start_bot()
                last_bot_restart = current_time
            else:
                logger.info("Waiting for cooldown before restarting bot...")
        
        # Check parser process
        if parser_proc and parser_proc.poll() is not None:
            if current_time - last_parser_restart > restart_cooldown:
                logger.warning(f"Parser process exited with code {parser_proc.poll()}, restarting...")
                parser_proc = start_parser()
                last_parser_restart = current_time
            else:
                logger.info("Waiting for cooldown before restarting parser...")
        
        # Sleep before checking again
        time.sleep(5)

if __name__ == "__main__":
    logger.info("Starting combined services...")
    
    # Make sure we have a bot token
    ensure_bot_token()
    
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