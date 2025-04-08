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
telethon_process = None
processor_process = None
message_queue = None

async def run_bot():
    """Start Telegram bot"""
    logger.info("Starting Telegram bot...")
    try:
        # Make sure Django is fully initialized before starting the bot
        import django
        os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
        django.setup()
        
        from tg_bot.bot import main
        await main()
    except Exception as e:
        logger.error(f"Error starting bot: {e}")
        logger.error(f"Traceback: {traceback.format_exc()}")
        raise

def run_telethon_parser(message_queue):
    """Start Telethon parser"""
    logger.info("Starting Telethon parser...")
    try:
        # Initialize Django first
        import django
        os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
        django.setup()
        
        # Import configuration
        from tg_bot.config import DATA_FOLDER
        
        # Create session directory if it doesn't exist
        session_dir = os.path.join(DATA_FOLDER, 'sessions')
        os.makedirs(session_dir, exist_ok=True)
        
        # Check for session files in multiple locations
        session_paths = [
            'telethon_user_session.session',
            'telethon_session.session',
            os.path.join(session_dir, 'telethon_user_session.session'),
            os.path.join(session_dir, 'telethon_session.session')
        ]
        
        session_exists = any(os.path.exists(path) for path in session_paths)
        
        if not session_exists:
            logger.warning("No Telethon session file found. Please authorize using the Telegram bot (🔐 Authorize Telethon) or run 'python -m tg_bot.auth_telethon'.")
            logger.warning("IMPORTANT: You must use a regular user account, NOT a bot!")
            logger.warning("Telethon parser will not be started.")
            return
            
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

async def run_services():
    """Main function to run all services"""
    global telethon_process, processor_process, message_queue
    
    start_time = datetime.now()
    logger.info(f"====== Starting bot services {start_time.strftime('%Y-%m-%d %H:%M:%S')} ======")
    
    # Create a queue for inter-process communication
    message_queue = multiprocessing.Queue()
    
    try:
        # Give Django server time to fully initialize - it's started by the start.sh script
        logger.info("Waiting for web server to be fully initialized...")
        await asyncio.sleep(3)
        
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
        
        # Wait for processes to initialize
        await asyncio.sleep(3)
        
        # Start bot
        await run_bot()
        
    except KeyboardInterrupt:
        logger.info("\nReceived termination signal (KeyboardInterrupt)")
    except Exception as e:
        logger.error(f"Critical error during service execution: {e}")
        logger.error(f"Traceback: {traceback.format_exc()}")
    finally:
        # Always ensure proper shutdown
        await shutdown_services()
        
        # Log runtime information
        end_time = datetime.now()
        runtime = end_time - start_time
        logger.info(f"Bot services stopped. Runtime: {runtime}")
        logger.info("====== End ======")

async def shutdown_services():
    """Shutdown all services cleanly"""
    global telethon_process, processor_process
    
    logger.info("Stopping bot services...")
    
    # Stop Telethon parser
    if telethon_process and telethon_process.is_alive():
        logger.info("Stopping Telethon parser...")
        telethon_process.terminate()
        telethon_process.join(timeout=5)
        if telethon_process.is_alive():
            logger.warning("Telethon parser did not terminate gracefully, forcing...")
            os.kill(telethon_process.pid, signal.SIGKILL)
    
    # Stop message processor
    if processor_process and processor_process.is_alive():
        logger.info("Stopping message processor...")
        processor_process.terminate()
        processor_process.join(timeout=5)
        if processor_process.is_alive():
            logger.warning("Message processor did not terminate gracefully, forcing...")
            os.kill(processor_process.pid, signal.SIGKILL)

if __name__ == "__main__":
    logger.info("Starting Bot Process")
    
    try:
        asyncio.run(run_services())
    except Exception as e:
        logger.error(f"Fatal error in main process: {e}")
        logger.error(f"Traceback: {traceback.format_exc()}")
        sys.exit(1) 