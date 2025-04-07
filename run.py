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
import base64
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor
import json
import sqlite3
from telethon.sessions import StringSession

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
        from tg_bot.config import WEB_SERVER_HOST, WEB_SERVER_PORT, ADMIN_ID
        # Use 0.0.0.0 to listen on all interfaces in production
        host = WEB_SERVER_HOST
        port = WEB_SERVER_PORT
        logger.info(f"Django server configured to run on {host}:{port}")
        
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
        logger.error(f"Traceback: {traceback.format_exc()}")
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

def validate_telethon_session_file(session_file):
    """Validate that a Telethon session file is properly formatted"""
    try:
        # Check if the file exists and has content
        if not os.path.exists(session_file):
            logger.error(f"Session file does not exist: {session_file}")
            return False
            
        file_size = os.path.getsize(session_file)
        if file_size == 0:
            logger.error(f"Session file is empty: {session_file}")
            return False
            
        # Telethon session files are SQLite databases, try to open and validate
        try:
            conn = sqlite3.connect(session_file)
            cursor = conn.cursor()
            
            # Check if the expected tables exist
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
            tables = [row[0] for row in cursor.fetchall()]
            
            required_tables = ['sessions', 'entities']
            missing_tables = [table for table in required_tables if table not in tables]
            
            if missing_tables:
                logger.error(f"Session file is missing required tables: {', '.join(missing_tables)}")
                return False
                
            # Check if there's a valid session in the file
            cursor.execute("SELECT COUNT(*) FROM sessions;")
            session_count = cursor.fetchone()[0]
            
            if session_count == 0:
                logger.error(f"Session file has no sessions: {session_file}")
                return False
                
            # Session file appears valid
            logger.info(f"Session file validated: {session_file} (has {session_count} sessions)")
            return True
        except sqlite3.Error as e:
            logger.error(f"Failed to validate session file {session_file}: {e}")
            return False
    except Exception as e:
        logger.error(f"Unexpected error validating session file {session_file}: {e}")
        return False

def ensure_telethon_session():
    """Ensure Telethon session exists and is valid"""
    import os
    import base64
    import logging
    from telethon.sessions import StringSession
    logger = logging.getLogger('run_script')
    
    logger.info("Checking for Telethon session...")
    
    # Check for session in environment variables
    session_data = os.getenv('TELETHON_SESSION')
    if session_data:
        logger.info("Found Telethon session in environment variables. Using it.")
        try:
            # Add padding if necessary
            padding = 4 - (len(session_data) % 4)
            if padding != 4:
                session_data += '=' * padding
                logger.info(f"Fixed base64 padding (added {padding} padding characters)")
                
            # Try to decode base64
            try:
                decoded_data = base64.b64decode(session_data)
                logger.info("Successfully decoded base64 session data")
                return True
            except Exception as e:
                logger.error(f"Failed to decode base64 session data: {e}")
                logger.error(f"Original length: {len(session_data)}, After padding: {len(session_data)}")
                return False
        except Exception as e:
            logger.error(f"Error processing session data: {e}")
            return False
    else:
        logger.warning("No Telethon session found in environment variables")
        return False

async def initialize_telethon_client(session_name):
    """Initialize a Telethon client with the given session name"""
    from telethon import TelegramClient
    from tg_bot.config import API_ID, API_HASH
    
    # Check if session file exists
    if not os.path.exists(f"{session_name}.session"):
        logger.warning(f"Session file {session_name}.session does not exist")
        return None
    
    # Initialize client with longer timeouts
    client = TelegramClient(session_name, API_ID, API_HASH, 
                           connection_retries=10, 
                           retry_delay=5)
    
    # Connect and test authorization
    try:
        logger.info(f"Attempting to connect with session: {session_name}")
        await client.connect()
        
        if not await client.is_user_authorized():
            logger.error(f"Session {session_name} is not authorized")
            await client.disconnect()
            return None
        
        # Test with a simple call
        me = await client.get_me()
        logger.info(f"Successfully authenticated as {me.first_name} (@{me.username})")
        return client
    except Exception as e:
        logger.error(f"Error testing client connection: {e}")
        import traceback
        logger.error(f"Traceback: {traceback.format_exc()}")
        
        try:
            await client.disconnect()
        except:
            pass
        return None

async def create_fresh_telethon_session():
    """
    Creates a new Telethon session file using API credentials.
    NOTE: This just creates a new session file, it doesn't perform phone auth
    which would require user interaction. This is mainly useful for bots.
    """
    from telethon import TelegramClient
    from tg_bot.config import API_ID, API_HASH
    
    session_name = "telethon_new_session"
    
    try:
        logger.info(f"Creating new Telethon session: {session_name}")
        client = TelegramClient(session_name, API_ID, API_HASH)
        
        # Just connect to create the session file
        await client.connect()
        
        # Test connection
        if client.is_connected():
            logger.info(f"Successfully created new session file: {session_name}.session")
            
            # We're not authorized with this new session,
            # but at least we have a valid session file structure
            await client.disconnect()
            
            # Copy the new session to standard name
            import shutil
            try:
                shutil.copy(f"{session_name}.session", "telethon_session.session")
                logger.info("Copied new session to standard filename")
            except Exception as e:
                logger.error(f"Error copying session file: {e}")
                
            return True
        else:
            logger.error("Failed to connect with new session")
            return False
    except Exception as e:
        logger.error(f"Error creating new Telethon session: {e}")
        import traceback
        logger.error(f"Traceback: {traceback.format_exc()}")
        return False

async def auth_with_existing_session():
    """
    Створює нову сесію, ініціалізуючи її з існуючого файлу сесії (test_session.session)
    """
    import shutil
    from telethon import TelegramClient
    from tg_bot.config import API_ID, API_HASH
    
    # Перевіряємо наявність файлу test_session.session
    if not os.path.exists('test_session.session'):
        logger.error("test_session.session file not found")
        return False
    
    # Копіюємо файл сесії
    try:
        shutil.copy('test_session.session', 'telethon_session.session')
        logger.info("Copied test_session.session to telethon_session.session")
    except Exception as e:
        logger.error(f"Error copying test_session.session: {e}")
        return False
    
    # Ініціалізуємо клієнт з новою сесією
    client = TelegramClient('telethon_session', API_ID, API_HASH)
    
    try:
        # Підключаємось
        await client.connect()
        
        # Перевіряємо авторизацію
        if not await client.is_user_authorized():
            logger.error("Session was copied but is not authorized")
            await client.disconnect()
            return False
        
        # Отримуємо інформацію про користувача
        me = await client.get_me()
        logger.info(f"Successfully authenticated with test_session as: {me.first_name} (@{me.username})")
        
        # Від'єднуємось (клієнт буде повторно ініціалізований в основному процесі)
        await client.disconnect()
        
        return True
    except Exception as e:
        logger.error(f"Error authenticating with test_session: {e}")
        import traceback
        logger.error(f"Traceback: {traceback.format_exc()}")
        try:
            await client.disconnect()
        except:
            pass
        return False

def run_telethon_parser(message_queue):
    """Start Telethon parser"""
    logger.info("Starting Telethon parser...")
    try:
        # Make sure Django is fully initialized before starting the parser
        # as it depends on Django ORM models
        import django
        os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
        django.setup()
        
        # Import here to avoid circular imports
        from tg_bot.telethon_worker import telethon_task
        
        # Create event loop for this process
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        try:
            # Run the telethon task with the message queue
            loop.run_until_complete(telethon_task(message_queue))
        except KeyboardInterrupt:
            logger.info("Interrupted")
        except Exception as e:
            logger.error(f"Error in telethon task: {e}")
            logger.error(f"Traceback: {traceback.format_exc()}")
        finally:
            loop.close()
            
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