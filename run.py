import subprocess
import sys
import os
import signal
import asyncio
import logging
import multiprocessing
import queue
import time
import traceback
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor

# Configuration of logging for the entire project
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S',
    handlers=[
        logging.StreamHandler(),  # Output to console
        logging.FileHandler('app.log', encoding='utf-8')  # Write to file
    ]
)
logger = logging.getLogger('run_script')

# Global variables to track processes
django_process = None
telethon_process = None
processor_process = None
message_queue = None

def run_django():
    """Start Django server"""
    logger.info("Starting Django server...")
    try:
        from tg_bot.config import WEB_SERVER_HOST, WEB_SERVER_PORT
        
        # Always use 127.0.0.1 for the bot's internal Django server
        host = "127.0.0.1"
        port = WEB_SERVER_PORT
        
        django_process = subprocess.Popen(
            [sys.executable, 'manage.py', 'runserver', f"{host}:{port}"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            universal_newlines=True
        )
        logger.info(f"Django server started (PID: {django_process.pid})")
        
        # Check if Django started successfully
        for i in range(5):  # Try for 5 seconds
            if django_process.poll() is not None:
                stdout, stderr = django_process.communicate()
                logger.error(f"Django server failed to start: {stderr}")
                return None
            time.sleep(1)
            
        return django_process
    except Exception as e:
        logger.error(f"Error starting Django server: {e}")
        return None

async def run_bot():
    """Start Telegram bot"""
    logger.info("Starting Telegram bot...")
    try:
        # Make sure Django is fully initialized before starting the bot
        # as it depends on Django ORM models
        import django
        os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
        django.setup()
        
        from tg_bot.bot import main
        await main()
    except Exception as e:
        logger.error(f"Error starting bot: {e}")
        logger.error(f"Traceback: {traceback.format_exc()}")

def run_telethon_parser(message_queue):
    """Start Telethon parser"""
    logger.info("Starting Telethon parser...")
    try:
        # Check if any user session file exists (either from bot or console)
        if not (os.path.exists('telethon_user_session.session') or os.path.exists('telethon_session.session')):
            logger.warning("No Telethon session file found. Please authorize using the Telegram bot (🔐 Authorize Telethon) or run 'python -m tg_bot.auth_telethon'.")
            logger.warning("IMPORTANT: You must use a regular user account, NOT a bot!")
            logger.warning("Telethon parser will not be started.")
            return
            
        # Make sure Django is fully initialized before starting the parser
        # as it depends on Django ORM models
        import django
        os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
        django.setup()
        
        from tg_bot.telethon_worker import telethon_worker_process
        telethon_worker_process(message_queue)
    except Exception as e:
        logger.error(f"Error starting Telethon parser: {e}")
        logger.error(f"Traceback: {traceback.format_exc()}")

def message_processor(message_queue):
    """Process messages from Telethon parser"""
    logger.info("Starting message processor...")
    try:
        # Initialize Django
        import django
        os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
        django.setup()
        
        while True:
            try:
                # Get message from queue (if queue is empty, wait)
                message = message_queue.get(block=True, timeout=1)
                logger.debug(f"Received message from queue: {message.get('message_info', {}).get('message_id')}")
            except queue.Empty:
                continue
            except Exception as e:
                logger.error(f"Error processing message: {e}")
    except Exception as e:
        logger.error(f"Fatal error in message processor: {e}")
        logger.error(f"Traceback: {traceback.format_exc()}")

def run_services():
    """Main function to run all services"""
    global django_process, telethon_process, processor_process, message_queue
    
    start_time = datetime.now()
    logger.info(f"====== Starting services {start_time.strftime('%Y-%m-%d %H:%M:%S')} ======")
    
    # Create a queue for inter-process communication
    message_queue = multiprocessing.Queue()
    
    try:
        # Start Django server first - if this fails, we'll exit early
        django_process = run_django()
        if not django_process:
            logger.error("Failed to start Django server. Aborting startup.")
            return
        
        # Allow Django to fully initialize before starting other services
        time.sleep(3)
        
        # Start message processor
        processor_process = multiprocessing.Process(
            target=message_processor,
            args=(message_queue,)
        )
        processor_process.daemon = True
        processor_process.start()
        logger.info(f"Message processor process started (PID: {processor_process.pid})")
        
        # Start Telethon parser
        telethon_process = multiprocessing.Process(
            target=run_telethon_parser,
            args=(message_queue,)
        )
        telethon_process.daemon = True
        telethon_process.start()
        logger.info(f"Telethon parser process started (PID: {telethon_process.pid})")
        
        # Start bot in event loop
        try:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            loop.run_until_complete(run_bot())
        except KeyboardInterrupt:
            logger.info("\nReceived termination signal (KeyboardInterrupt)")
        except Exception as e:
            logger.error(f"Error in bot event loop: {e}")
            logger.error(f"Traceback: {traceback.format_exc()}")
        finally:
            if loop and not loop.is_closed():
                # Cancel all remaining tasks
                for task in asyncio.all_tasks(loop):
                    task.cancel()
                
                # Run the event loop once more to let it process the cancellations
                try:
                    loop.run_until_complete(asyncio.sleep(0.1))
                except asyncio.CancelledError:
                    pass
                
                loop.close()
                logger.info("Event loop closed")
    
    except KeyboardInterrupt:
        logger.info("\nReceived termination signal (KeyboardInterrupt)")
    except Exception as e:
        logger.error(f"Critical error during service execution: {e}")
        logger.error(f"Traceback: {traceback.format_exc()}")
    finally:
        # Always ensure proper shutdown
        shutdown_services()
        
        # Log runtime information
        end_time = datetime.now()
        runtime = end_time - start_time
        logger.info(f"Services stopped. Runtime: {runtime}")
        logger.info("====== End ======")

def shutdown_services():
    """Shutdown all services cleanly"""
    global django_process, telethon_process, processor_process
    
    logger.info("Stopping services...")
    
    # Stop Telethon parser
    if telethon_process and telethon_process.is_alive():
        logger.info("Stopping Telethon parser...")
        telethon_process.terminate()
        telethon_process.join(timeout=5)
        if telethon_process.is_alive():
            logger.warning("Telethon parser did not terminate gracefully, forcing...")
            if sys.platform == 'win32':
                telethon_process.kill()
            else:
                os.kill(telethon_process.pid, signal.SIGKILL)
    
    # Stop message processor
    if processor_process and processor_process.is_alive():
        logger.info("Stopping message processor...")
        processor_process.terminate()
        processor_process.join(timeout=5)
        if processor_process.is_alive():
            logger.warning("Message processor did not terminate gracefully, forcing...")
            if sys.platform == 'win32':
                processor_process.kill()
            else:
                os.kill(processor_process.pid, signal.SIGKILL)
    
    # Stop Django server
    if django_process:
        logger.info("Stopping Django server...")
        if sys.platform == 'win32':
            subprocess.call(['taskkill', '/F', '/T', '/PID', str(django_process.pid)])
        else:
            django_process.terminate()
            django_process.wait(timeout=5)

def signal_handler(signum, frame):
    """Handle termination signals"""
    logger.info(f"Received signal {signum}. Initiating shutdown...")
    shutdown_services()
    sys.exit(0)

if __name__ == "__main__":
    # Set the limit on the number of open files for Windows
    if sys.platform.startswith('win'):
        try:
            import win32file
            win32file._setmaxstdio(2048)
        except:
            pass
    
    # Set up signal handlers
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    run_services() 