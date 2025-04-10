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
import shutil
import glob
import re
import psutil
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

# Set up the logs directory first
try:
    os.makedirs('logs', exist_ok=True)
except Exception:
    pass

# Configuration of logging for the entire project
try:
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S',
        handlers=[
            logging.StreamHandler(),  # Output to console
            logging.FileHandler('logs/app.log', encoding='utf-8', mode='a')  # Write to file
        ]
    )
except Exception as e:
    # Fallback to console-only logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S',
        handlers=[
            logging.StreamHandler(),  # Output to console only
        ]
    )
    print(f"Warning: Could not set up file logging: {e}. Using console logging only.")

logger = logging.getLogger('run_script')

# Global variables to track processes
django_process = None
telethon_process = None
processor_process = None
message_queue = None
should_exit = False

def run_command(command, description="Running command", critical=False):
    """Run a shell command and log the output."""
    logger.info(f"{description}: {command}")
    
    try:
        result = subprocess.run(
            command, 
            shell=True, 
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        logger.info(f"Command output: {result.stdout.strip()}")
        return True
    except subprocess.CalledProcessError as e:
        logger.error(f"Command failed with exit code {e.returncode}")
        logger.error(f"Error output: {e.stderr.strip()}")
        
        if critical:
            logger.critical("Critical command failed. Exiting.")
            sys.exit(1)
        return False

def ensure_directories():
    """Create all necessary directories for the project."""
    BASE_DIR = Path(__file__).resolve().parent
    
    # Essential directories
    directories = [
        'logs', 'logs/bot',
        'media', 'media/messages',
        'static', 'static/img',
        'staticfiles', 'staticfiles/img',
        'templates', 'templates/admin_panel',
        'data', 'data/sessions'
    ]
    
    for directory in directories:
        dir_path = BASE_DIR / directory
        os.makedirs(dir_path, exist_ok=True)
        logger.info(f"Directory ensured: {dir_path}")
    
    # Create placeholder health files
    health_files = [
        ('health.txt', 'OK'),
        ('healthz.txt', 'OK'),
        ('health.html', '<html><body>OK</body></html>'),
        ('healthz.html', '<html><body>OK</body></html>')
    ]
    
    for filename, content in health_files:
        # Create in root
        with open(os.path.join(BASE_DIR, filename), 'w') as f:
            f.write(content)
        
        # Create in static directories
        with open(os.path.join(BASE_DIR, 'static', filename), 'w') as f:
            f.write(content)
        with open(os.path.join(BASE_DIR, 'staticfiles', filename), 'w') as f:
            f.write(content)
    
    logger.info("All required directories and health files created")
    return True

def fix_migration_conflict():
    """Fix Django migration conflicts."""
    logger.info("Checking for migration conflicts...")
    
    try:
        # Set up Django
        import django
        os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
        django.setup()
        
        # Create migrations directory if it doesn't exist
        for app in ['admin_panel', 'tg_bot']:
            migrations_dir = os.path.join(app, 'migrations')
            os.makedirs(migrations_dir, exist_ok=True)
            # Create __init__.py if it doesn't exist
            init_file = os.path.join(migrations_dir, '__init__.py')
            if not os.path.exists(init_file):
                with open(init_file, 'w') as f:
                    pass
        
        # Radical approach: Remove all migration files and start fresh
        logger.info("Taking radical approach to fix migrations: removing all migrations")
        for app in ['admin_panel', 'tg_bot']:
            migration_files = glob.glob(f"{app}/migrations/*.py")
            for file in migration_files:
                if '__init__.py' not in file:
                    try:
                        logger.info(f"Removing migration file: {file}")
                        os.remove(file)
                    except Exception as e:
                        logger.warning(f"Could not remove {file}: {e}")
        
        # Create initial migrations
        logger.info("Creating fresh migrations")
        run_command("python manage.py makemigrations admin_panel", "Creating admin_panel migrations")
        run_command("python manage.py makemigrations tg_bot", "Creating tg_bot migrations")
        
        # Try to migrate with fake-initial
        logger.info("Applying migrations with fake-initial")
        run_command("python manage.py migrate --fake-initial", "Applying initial migrations with fake")
        
        # Apply migrations normally
        logger.info("Applying migrations normally")
        run_command("python manage.py migrate", "Applying migrations", critical=False)
        
        # Collect static
        logger.info("Collecting static files")
        run_command("python manage.py collectstatic --noinput", "Collecting static")
        
        logger.info("Migration conflicts resolved successfully")
        return True
        
    except Exception as e:
        logger.error(f"Error fixing migration conflicts: {e}")
        logger.error(traceback.format_exc())
        return False

def find_and_kill_telegram_processes():
    """Find and kill any running telegram bot processes"""
    logger.info("Checking for running telegram bot processes")
    
    # Get the current process ID to avoid killing ourselves
    current_pid = os.getpid()
    
    killed_processes = 0
    for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
        try:
            # Skip our own process
            if proc.info['pid'] == current_pid:
                continue
                
            # Check if this is a python process running a bot
            if proc.info['name'] and 'python' in proc.info['name'].lower():
                cmdline = proc.info['cmdline']
                if cmdline and any('bot.py' in cmd for cmd in cmdline if cmd):
                    logger.info(f"Found running bot process: {proc.info['pid']}")
                    
                    # Kill the process
                    try:
                        os.kill(proc.info['pid'], signal.SIGTERM)
                        logger.info(f"Successfully terminated process {proc.info['pid']}")
                        killed_processes += 1
                        # Give process time to shut down
                        time.sleep(2)
                    except Exception as e:
                        logger.error(f"Failed to kill process {proc.info['pid']}: {str(e)}")
        except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
            pass
    
    if killed_processes > 0:
        logger.info(f"Killed {killed_processes} bot processes")
    else:
        logger.info("No running bot processes found")
    
    return killed_processes

def run_django():
    """Start Django server"""
    logger.info("Starting Django server...")
    try:
        # Setup Django settings module
        os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
        
        # Try to load the config, but use defaults if it fails
        try:
            from tg_bot.config import WEB_SERVER_HOST, WEB_SERVER_PORT
            # Use 127.0.0.1 instead of localhost to avoid IPv6 issues
            host = "127.0.0.1" if WEB_SERVER_HOST == "localhost" else WEB_SERVER_HOST
            port = WEB_SERVER_PORT
        except Exception as e:
            logger.warning(f"Could not load config from tg_bot.config: {e}")
            host = os.environ.get('WEB_SERVER_HOST', '127.0.0.1')
            port = os.environ.get('WEB_SERVER_PORT', '8000')
            logger.info(f"Using default host: {host}, port: {port}")
        
        # If running on Railway, use the PORT environment variable
        if os.environ.get('RAILWAY_ENVIRONMENT'):
            port = os.environ.get('PORT', '8000')
            # Use Gunicorn on Railway
            cmd = f"gunicorn core.wsgi:application --preload --workers 2 --threads 2 --bind 0.0.0.0:{port}"
            logger.info(f"Starting Django with Gunicorn: {cmd}")
            django_process = subprocess.Popen(
                cmd,
                shell=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                universal_newlines=True
            )
        else:
            # Use Django's development server locally - use array format to avoid path issues with spaces
            logger.info(f"Starting Django development server on {host}:{port}")
            django_process = subprocess.Popen(
                [sys.executable, "manage.py", "runserver", f"{host}:{port}"],
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
        logger.error(traceback.format_exc())
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
        
        # First check and kill any existing bot processes
        find_and_kill_telegram_processes()
        
        # Create a bot lock file
        with open('bot.lock', 'w') as f:
            f.write(str(os.getpid()))
        logger.info(f"Created bot lock file with PID {os.getpid()}")
        
        # Check for required environment variables
        bot_token = os.environ.get('BOT_TOKEN')
        if not bot_token:
            # Try to get from .env file
            try:
                from dotenv import load_dotenv
                load_dotenv()
                bot_token = os.environ.get('BOT_TOKEN')
            except ImportError:
                pass
            
        if not bot_token:
            # Try to get from config.py
            try:
                from tg_bot.config import TOKEN_BOT
                if TOKEN_BOT:
                    bot_token = TOKEN_BOT
                    logger.info("Using bot token from config.py")
                    # Set it in environment for other processes
                    os.environ['BOT_TOKEN'] = TOKEN_BOT
            except Exception as e:
                logger.error(f"Error getting bot token from config.py: {e}")
                
        if not bot_token:
            # Try to get from database
            try:
                from admin_panel.models import BotSettings
                bot_settings = BotSettings.objects.first()
                if bot_settings and bot_settings.bot_token:
                    bot_token = bot_settings.bot_token
                    logger.info("Using bot token from database")
                    # Set it in environment for other processes
                    os.environ['BOT_TOKEN'] = bot_token
            except Exception as e:
                logger.error(f"Error getting bot token from database: {e}")
        
        # Last resort backup token
        if not bot_token:
            bot_token = "8102516142:AAFTsVXXujHHKoX2KZGqZXBHPBznfgh7kg0"
            logger.warning("Using backup hard-coded bot token")
            os.environ['BOT_TOKEN'] = bot_token
            
        # Initialize aiogram directly
        logger.info("Initializing Telegram bot with aiogram...")
        try:
            from aiogram import Bot, Dispatcher, types, F
            from aiogram.fsm.storage.memory import MemoryStorage
            
            # Initialize bot and dispatcher
            bot = Bot(token=bot_token)
            storage = MemoryStorage()
            dp = Dispatcher(storage=storage)
            
            # Check bot token by getting info
            bot_info = await bot.get_me()
            logger.info(f"Bot initiated successfully: @{bot_info.username} (ID: {bot_info.id})")
            
            # Try to register handlers from tg_bot
            try:
                from tg_bot.middlewares import ChannelsDataMiddleware
                from tg_bot.handlers import common_router, admin_router, session_router
                
                # Add middleware
                dp.message.middleware(ChannelsDataMiddleware())
                dp.callback_query.middleware(ChannelsDataMiddleware())
                
                # Register routers
                dp.include_router(session_router)
                dp.include_router(admin_router)
                dp.include_router(common_router)
                logger.info("Bot handlers registered successfully")
            except Exception as handler_error:
                logger.error(f"Error registering handlers: {handler_error}")
                
                # Create basic handlers if the regular ones failed
                @dp.message(F.text == "/start")
                async def cmd_start(message: types.Message):
                    await message.answer(f"Hello, {message.from_user.first_name}! Bot is running in emergency mode.")
                
                @dp.message(F.text == "/help")
                async def cmd_help(message: types.Message):
                    await message.answer("This bot is running in emergency mode. Regular functionality is limited.")
                
                logger.info("Emergency handlers registered")
            
            # Start polling
            logger.info("Starting bot polling...")
            await bot.delete_webhook(drop_pending_updates=True)
            await dp.start_polling(bot, allowed_updates=dp.resolve_used_update_types())
            
        except Exception as aiogram_error:
            logger.error(f"Critical error in aiogram init: {aiogram_error}")
            logger.error(traceback.format_exc())
            
            # Try fallback method only if aiogram init fails
            logger.info("Trying fallback method...")
            from tg_bot.bot import main
            await main()
        
    except Exception as e:
        logger.error(f"Error starting bot: {e}")
        logger.error(f"Traceback: {traceback.format_exc()}")
        
        # Try to load fallback bot implementation
        try:
            logger.info("Trying fallback bot implementation...")
            from tg_bot.launcher import run as run_bot_fallback
            await run_bot_fallback()
        except Exception as e2:
            logger.error(f"Fallback bot also failed: {e2}")
            logger.error(f"Traceback: {traceback.format_exc()}")

def run_telethon_parser(message_queue):
    """Start Telethon parser"""
    logger.info("Starting Telethon parser...")
    try:
        import django
        os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
        django.setup()
        
        # Check for Telethon sessions in the database first
        has_active_session = False
        try:
            from admin_panel.models import TelegramSession
            sessions = TelegramSession.objects.filter(is_active=True)
            if sessions.exists():
                logger.info(f"Found {sessions.count()} active Telethon sessions in database")
                has_active_session = True
                
                # Try to extract session data if available
                for session in sessions:
                    if hasattr(session, 'session_data') and session.session_data:
                        logger.info(f"Found session data for {session.name}, creating session file")
                        session_file = f"{session.name}.session"
                        with open(session_file, 'wb') as f:
                            f.write(session.session_data)
                        logger.info(f"Created session file: {session_file}")
            else:
                logger.warning("No active Telethon sessions found in database")
        except Exception as e:
            logger.error(f"Error checking database sessions: {e}")
        
        # Check if any user session file exists (either from bot or console)
        session_files = glob.glob('*.session')
        session_files = [f for f in session_files if 'telethon' in f.lower() or 'session' in f.lower()]
        
        if not session_files and not has_active_session:
            logger.warning("No Telethon session file found. Please authorize using the Telegram bot (🔐 Authorize Telethon) or run 'python -m tg_bot.auth_telethon'.")
            logger.warning("IMPORTANT: You must use a regular user account, NOT a bot!")
            logger.warning("Telethon parser will not be started.")
            
            # Try to create a session automatically if credentials exist
            try:
                logger.info("Attempting to create a Telethon session automatically...")
                from dotenv import load_dotenv
                load_dotenv()
                
                api_id = os.environ.get('API_ID')
                api_hash = os.environ.get('API_HASH')
                session_name = os.environ.get('SESSION_NAME', 'telethon_session')
                
                if api_id and api_hash:
                    logger.info("Found API credentials, running auth session creation...")
                    # Use alternative approach since we can't provide user input here
                    from telethon import TelegramClient
                    from telethon.sessions import StringSession
                    
                    # Just create the session file, we'll need user interaction later
                    client = TelegramClient(session_name, int(api_id), api_hash)
                    
                    # Try to connect but don't wait for login
                    async def init_session():
                        await client.connect()
                        if await client.is_user_authorized():
                            logger.info("Session already authorized!")
                        else:
                            logger.info("Session created but not authorized. Use the Telegram bot to authorize it.")
                    
                    # Run the async function
                    loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(loop)
                    try:
                        loop.run_until_complete(init_session())
                    finally:
                        loop.close()
                        
                    logger.info(f"Created session file: {session_name}.session")
                    logger.info("You'll need to authenticate this session through the Telegram bot.")
                else:
                    logger.warning("No API credentials found. Please set API_ID and API_HASH environment variables.")
            except Exception as e:
                logger.error(f"Error creating automatic session: {e}")
                logger.error(traceback.format_exc())
            
            # Can't proceed without a session
            return
            
        logger.info("Starting Telethon worker process...")
        # Make sure we have all required files
        for filename in ['file.json', 'categories.json']:
            if not os.path.exists(filename):
                logger.info(f"Creating empty {filename}")
                with open(filename, 'w') as f:
                    f.write('{}')
                    
        # Start the parser
        from tg_bot.telethon_worker import telethon_worker_process
        telethon_worker_process(message_queue)
    
    except ImportError as ie:
        logger.error(f"Import error in Telethon parser: {ie}")
        logger.error("This usually means a required package is missing")
        logger.error("Try installing: pip install telethon")
        try:
            # Try to install required package
            run_command("pip install telethon", "Installing telethon")
            logger.info("Telethon installed, try running again")
        except:
            pass
    except Exception as e:
        logger.error(f"Error starting Telethon parser: {e}")
        logger.error(f"Traceback: {traceback.format_exc()}")
        
        # Try alternative method
        try:
            logger.info("Trying alternative Telethon startup method...")
            from tg_bot.session_manager import start_session_manager
            start_session_manager(message_queue)
        except Exception as e2:
            logger.error(f"Alternative Telethon method also failed: {e2}")
            logger.error(f"Traceback: {traceback.format_exc()}")

def message_processor(message_queue):
    """Process messages from Telethon parser"""
    logger.info("Starting message processor...")
    
    # Initialize Django
    try:
        import django
        os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
        django.setup()
        
        # Import models here to ensure they're loaded after Django setup
        try:
            from admin_panel.models import Message, Channel
            logger.info("Successfully imported Django models")
        except Exception as model_error:
            logger.error(f"Error importing Django models: {model_error}")
    except Exception as e:
        logger.error(f"Error initializing Django for message processor: {e}")
        logger.error(traceback.format_exc())
        return
    
    restart_delay = 5  # seconds between retries
    
    while True:
        try:
            # Get message from queue (if queue is empty, wait)
            try:
                message = message_queue.get(block=True, timeout=1)
                logger.debug(f"Received message from queue: {message.get('message_info', {}).get('message_id')}")
                
                # Process the message
                try:
                    # Get message info
                    message_info = message.get('message_info', {})
                    channel_info = message.get('channel_info', {})
                    
                    # Log basic info
                    logger.info(f"Processing message: {message_info.get('message_id')} from {channel_info.get('title')}")
                    
                    # Here you would typically save to database
                    # This is just a placeholder for the actual message processing logic
                    try:
                        from admin_panel.models import Message, Channel
                        
                        # Find or create channel
                        channel, created = Channel.objects.get_or_create(
                            channel_id=channel_info.get('id'),
                            defaults={
                                'title': channel_info.get('title'),
                                'username': channel_info.get('username')
                            }
                        )
                        
                        # Create message
                        Message.objects.create(
                            message_id=message_info.get('message_id'),
                            text=message_info.get('text', ''),
                            channel=channel,
                            date=message_info.get('date'),
                        )
                        logger.info(f"Saved message {message_info.get('message_id')} to database")
                    except Exception as db_error:
                        logger.error(f"Error saving message to database: {db_error}")
                        
                except Exception as process_error:
                    logger.error(f"Error processing message: {process_error}")
                    logger.error(traceback.format_exc())
                
            except queue.Empty:
                # Queue is empty, just continue waiting
                continue
                
        except KeyboardInterrupt:
            logger.info("Message processor interrupted by user")
            break
        except Exception as e:
            logger.error(f"Critical error in message processor: {e}")
            logger.error(traceback.format_exc())
            # Sleep before restarting the loop to avoid tight error loops
            time.sleep(restart_delay)
            # Increase delay for next restart (with a maximum)
            restart_delay = min(restart_delay * 2, 60)

def collect_static_files():
    """Collect static files for Django."""
    logger.info("Collecting static files...")
    try:
        run_command("python manage.py collectstatic --noinput", "Collecting static files")
        return True
    except Exception as e:
        logger.error(f"Error collecting static files: {e}")
        return False

def apply_fixes():
    """Apply all necessary fixes before starting services"""
    logger.info("Applying fixes and ensuring project setup...")
    
    # Create directories
    ensure_directories()
    
    try:
        # Fix migration conflicts - don't exit if this fails
        fix_migration_conflict()
    except Exception as e:
        logger.error(f"Error during migration fix: {e}")
        logger.error("Continuing startup despite migration issues")
    
    try:
        # Collect static files
        collect_static_files()
    except Exception as e:
        logger.error(f"Error collecting static files: {e}")
        logger.error("Continuing startup despite static files issues")
    
    # Check for and terminate any stray bot processes
    find_and_kill_telegram_processes()
    
    logger.info("All fixes applied")
    return True

def run_services():
    """Main function to run all services"""
    global django_process, telethon_process, processor_process, message_queue, should_exit
    
    start_time = datetime.now()
    logger.info(f"====== Starting services {start_time.strftime('%Y-%m-%d %H:%M:%S')} ======")
    
    # Set important environment variables
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
    
    # Check for missing packages - critical for Railway deployment
    try:
        fix_missing_packages()
    except Exception as e:
        logger.error(f"Error checking for missing packages: {e}")
        logger.error("Continuing despite package check errors")
    
    # Apply fixes and ensure everything is set up
    try:
        apply_fixes()
    except Exception as e:
        logger.error(f"Error applying fixes: {e}")
        logger.error("Continuing despite fix errors")
    
    # Load environment variables from .env if exists
    try:
        from dotenv import load_dotenv
        load_dotenv()
        logger.info("Loaded environment variables from .env file")
    except ImportError:
        logger.warning("python-dotenv not installed, skipping .env loading")
    except Exception as e:
        logger.error(f"Error loading .env file: {e}")
    
    # Create a queue for inter-process communication
    message_queue = multiprocessing.Queue()
    
    # Track if we should keep running
    should_continue = True
    retry_count = 0
    max_retries = 3
    should_exit = False
    
    while should_continue and retry_count < max_retries and not should_exit:
        try:
            # Start Django server first - if this fails, we'll retry
            django_process = run_django()
            if not django_process:
                logger.error("Failed to start Django server. Retrying...")
                retry_count += 1
                time.sleep(2)
                continue
            
            # Allow Django to fully initialize before starting other services
            logger.info("Waiting for Django to initialize...")
            time.sleep(5)
            
            # Check if Django is still running
            if django_process and django_process.poll() is not None:
                logger.error("Django server stopped unexpectedly. Retrying...")
                django_process = None
                retry_count += 1
                continue
            
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
            
            # Reset retry count as we've successfully started services
            retry_count = 0
            
            # Start bot in event loop
            try:
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                asyncio.run_coroutine_threadsafe(run_bot(), loop)
                
                # Keep the main thread running and check for exit flag
                while not should_exit and should_continue:
                    time.sleep(1)
                    # Check if Django is still running
                    if django_process and django_process.poll() is not None:
                        logger.error("Django server stopped unexpectedly.")
                        should_continue = False
                        break
            except KeyboardInterrupt:
                logger.info("\nReceived termination signal (KeyboardInterrupt)")
                should_continue = False
            except Exception as e:
                logger.error(f"Error in bot event loop: {e}")
                logger.error(f"Traceback: {traceback.format_exc()}")
                
                # Only retry if it wasn't a keyboard interrupt
                retry_count += 1
                logger.info(f"Retrying... ({retry_count}/{max_retries})")
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
            
            # If we got here and should_continue is still True, it means 
            # something crashed and we should retry
            if should_continue and not should_exit:
                logger.info("Service crashed, cleaning up before retry...")
                shutdown_services()
                time.sleep(5)  # Wait before restarting
                
        except KeyboardInterrupt:
            logger.info("\nReceived termination signal (KeyboardInterrupt)")
            should_continue = False
        except Exception as e:
            logger.error(f"Critical error during service execution: {e}")
            logger.error(f"Traceback: {traceback.format_exc()}")
            retry_count += 1
            logger.info(f"Retrying... ({retry_count}/{max_retries})")
            time.sleep(5)  # Wait before restarting
    
    # Final cleanup
    shutdown_services()
    
    # Log runtime information
    end_time = datetime.now()
    runtime = end_time - start_time
    logger.info(f"Services stopped. Runtime: {runtime}")
    logger.info("====== End ======")
    
    # If we exited because of too many retries, return error code
    if retry_count >= max_retries:
        logger.error(f"Too many retries ({max_retries}). Exiting.")
        sys.exit(1)

def shutdown_services():
    """Shutdown all services cleanly"""
    global django_process, telethon_process, processor_process
    
    logger.info("Stopping services...")
    
    # Helper function to safely terminate a process
    def safe_terminate(process, name):
        if not process:
            return
            
        try:
            # Only terminate if it's from the same process that created it
            if process.is_alive() if hasattr(process, 'is_alive') else process.poll() is None:
                logger.info(f"Stopping {name}...")
                
                if hasattr(process, 'terminate'):
                    process.terminate()
                    
                    # Give it time to terminate
                    timeout = 5
                    for _ in range(timeout):
                        if not (process.is_alive() if hasattr(process, 'is_alive') else process.poll() is None):
                            break
                        time.sleep(1)
                        
                    # Force kill if it's still running
                    if process.is_alive() if hasattr(process, 'is_alive') else process.poll() is None:
                        logger.warning(f"{name} did not terminate gracefully, forcing...")
                        if sys.platform == 'win32':
                            if hasattr(process, 'kill'):
                                process.kill()
                            else:
                                subprocess.call(['taskkill', '/F', '/T', '/PID', str(process.pid)])
                        else:
                            os.kill(process.pid, signal.SIGKILL)
                else:
                    # For subprocess.Popen objects
                    if sys.platform == 'win32':
                        subprocess.call(['taskkill', '/F', '/T', '/PID', str(process.pid)])
                    else:
                        process.terminate()
                        process.wait(timeout=5)
        except (psutil.NoSuchProcess, psutil.AccessDenied, AssertionError):
            # Process already gone or not our child
            pass
        except Exception as e:
            logger.error(f"Error stopping {name}: {e}")
    
    # Stop Telethon parser
    safe_terminate(telethon_process, "Telethon parser")
    
    # Stop message processor
    safe_terminate(processor_process, "Message processor")
    
    # Stop Django server
    safe_terminate(django_process, "Django server")
    
    # Remove bot lock file if it exists
    try:
        if os.path.exists('bot.lock'):
            os.remove('bot.lock')
            logger.info("Removed bot lock file")
    except Exception as e:
        logger.error(f"Error removing bot lock file: {e}")
        
    # Reset process variables
    telethon_process = None
    processor_process = None
    django_process = None

def signal_handler(signum, frame):
    """Handle termination signals"""
    logger.info(f"Received signal {signum}. Initiating shutdown...")
    # Don't call shutdown_services() directly from signal handler
    # This can cause multiprocessing issues
    global should_exit
    should_exit = True
    
    # If we're in the main process, set an exit flag instead
    # The main process will check this flag and shut down properly
    if 'should_continue' in globals():
        globals()['should_continue'] = False

def fix_missing_packages():
    """Install any missing packages that are required for the project."""
    logger.info("Checking for missing packages...")
    
    required_packages = [
        'dj-database-url',
        'whitenoise',
        'python-dotenv',
        'django-storages',
        'psycopg2-binary'
    ]
    
    for package in required_packages:
        try:
            # Try to import the package
            package_name = package.replace('-', '_')
            __import__(package_name)
            logger.info(f"Package {package} is already installed")
        except ImportError:
            # If import fails, install the package
            logger.warning(f"Package {package} is missing. Installing...")
            try:
                run_command(f"pip install {package}", f"Installing {package}")
                logger.info(f"Successfully installed {package}")
            except Exception as e:
                logger.error(f"Failed to install {package}: {e}")
    
    # Special case for psycopg2
    try:
        import psycopg2
        logger.info("psycopg2 is already installed")
    except ImportError:
        try:
            # Try to use binary version if regular fails
            import psycopg2_binary
            logger.info("psycopg2_binary is being used instead of psycopg2")
        except ImportError:
            logger.warning("psycopg2 is missing. Installing...")
            try:
                run_command("pip install psycopg2-binary", "Installing psycopg2-binary")
                logger.info("Successfully installed psycopg2-binary")
            except Exception as e:
                logger.error(f"Failed to install psycopg2-binary: {e}")
                
    return True

if __name__ == "__main__":
    # Set the limit on the number of open files for Windows
    if sys.platform.startswith('win'):
        try:
            import win32file
            win32file._setmaxstdio(2048)
        except:
            pass
    
    # Initialize exit flag
    should_exit = False
    
    # Set up signal handlers
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    # Create start-railway.sh for Railway deployment
    if os.environ.get('RAILWAY_ENVIRONMENT') or os.environ.get('RAILWAY_SERVICE_NAME'):
        with open('start-railway.sh', 'w') as f:
            f.write("#!/bin/bash\n")
            f.write("echo \"Starting application via run.py on Railway...\"\n")
            f.write("python run.py\n")
        os.chmod('start-railway.sh', 0o755)
        logger.info("Created Railway startup script")
    
    run_services() 