#!/usr/bin/env python
"""
Telegram parser script that can be run manually or as a background process.
"""
import os
import sys
import time
import asyncio
import django
import traceback
import multiprocessing
from threading import Thread
import logging
import signal

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S',
)
logger = logging.getLogger('manual_parser')

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')

# Add current directory to path to ensure imports work
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

try:
    django.setup()
    logger.info("Django setup successful")
except Exception as e:
    logger.error(f"Error during Django setup: {e}")
    logger.error(traceback.format_exc())
    # Continue anyway - some functionality might still work

# Import after Django setup
try:
    from multiprocessing import Queue
    from tg_bot.telethon_worker import telethon_worker_process
except ImportError as e:
    logger.error(f"Error importing required modules: {e}")
    logger.error(traceback.format_exc())
    sys.exit(1)

def signal_handler(sig, frame):
    """Handle process termination signals"""
    logger.info(f"Received signal {sig}, shutting down...")
    sys.exit(0)

def handle_messages_thread(queue):
    """
    Thread to handle messages from the queue
    """
    logger.info("Message handling thread started")
    while True:
        try:
            # Get a message from the queue (block until a message is available)
            message = queue.get()
            if message is None:
                logger.info("Received None message, exiting thread")
                break
                
            # Log the message
            logger.info(f"Received message from queue: {message.get('message_info', {}).get('message_id')}")
            
            # Process the message here
            # For example, you could do additional processing or trigger other actions
            
        except Exception as e:
            logger.error(f"Error in message handler thread: {e}")
            logger.error(traceback.format_exc())
        
        # Small delay to prevent high CPU usage
        time.sleep(0.01)
    
    logger.info("Message handling thread stopped")

if __name__ == "__main__":
    # Set up signal handlers
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    logger.info("Starting manual parser run...")
    
    try:
        # Create a message queue
        message_queue = Queue()
        
        # Start the message handler thread
        handler_thread = Thread(target=handle_messages_thread, args=(message_queue,))
        handler_thread.daemon = True
        handler_thread.start()
        logger.info("Started message handler thread")
        
        # Start the Telegram parser process
        parser_process = multiprocessing.Process(
            target=telethon_worker_process,
            args=(message_queue,)
        )
        parser_process.daemon = True  # Automatically terminate on parent exit
        parser_process.start()
        logger.info(f"Started parser process (PID: {parser_process.pid})")
        
        # Check if process started correctly
        if not parser_process.is_alive():
            logger.error("Parser process failed to start or terminated immediately")
            sys.exit(1)
        
        try:
            # Keep the main process running
            while parser_process.is_alive():
                time.sleep(1)
                
        except KeyboardInterrupt:
            logger.info("Keyboard interrupt received, shutting down...")
        finally:
            # Clean up
            logger.info("Shutting down parser process...")
            parser_process.terminate()
            parser_process.join(timeout=5)
            
            if parser_process.is_alive():
                logger.warning("Parser process did not terminate properly, killing...")
                parser_process.kill()
            
            logger.info("Shutting down message handler thread...")
            message_queue.put(None)  # Signal the thread to exit
            handler_thread.join(timeout=5)
            
    except Exception as e:
        logger.error(f"Error in main process: {e}")
        logger.error(traceback.format_exc())
        sys.exit(1)
    
    logger.info("Parser run completed")
    sys.exit(0) 