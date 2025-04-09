#!/usr/bin/env python3
"""
Файл для запуску Telegram бота в Railway.
Має перевірку помилок та надійний запуск.
"""
import os
import sys
import time
import signal
import logging
import traceback
import subprocess
from datetime import datetime
import asyncio
import io
import fcntl
import tempfile

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
        logging.FileHandler('logs/run_bot.log', encoding='utf-8'),
        logging.StreamHandler(sys.stdout)  # Use stdout instead of stderr for correct encoding
    ]
)
logger = logging.getLogger('run_bot')

# Ініціалізація Django
import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
try:
    django.setup()
    logger.info("Django successfully initialized")
except Exception as e:
    logger.error(f"Error initializing Django: {e}")
    logger.error(traceback.format_exc())

# Імпорт моделей Django
from admin_panel.models import BotSettings
from django.conf import settings

# Змінні для управління роботою
RETRY_INTERVAL = 30  # секунди між спробами перезапуску
MAX_RETRIES = 5      # максимальна кількість спроб перезапуску
running = True

# Global lock file to prevent multiple bot instances
if os.name == 'posix':  # Unix/Linux/MacOS
    LOCK_FILE = os.path.join(tempfile.gettempdir(), 'telegram_bot.lock')
    lock_file_handle = None
else:  # Windows doesn't have fcntl
    LOCK_FILE = os.path.join(tempfile.gettempdir(), 'telegram_bot.lock')
    lock_file_handle = None

def acquire_lock():
    """Acquire exclusive lock to ensure only one bot instance runs"""
    global lock_file_handle
    
    try:
        # Create or open the lock file
        lock_file_handle = open(LOCK_FILE, 'w')
        
        if os.name == 'posix':  # Unix/Linux/MacOS
            try:
                # Try to acquire an exclusive lock (non-blocking)
                fcntl.flock(lock_file_handle, fcntl.LOCK_EX | fcntl.LOCK_NB)
                logger.info(f"Acquired exclusive lock: {LOCK_FILE}")
            except IOError:
                # Failed to acquire lock - another instance is running
                logger.error("Failed to acquire lock - another bot instance is already running")
                lock_file_handle.close()
                lock_file_handle = None
                return False
        else:  # Windows - use a simpler approach
            try:
                # Check if the lock file is recent (less than 5 minutes old)
                if os.path.exists(LOCK_FILE):
                    mtime = os.path.getmtime(LOCK_FILE)
                    if time.time() - mtime < 300:  # 5 minutes
                        try:
                            with open(LOCK_FILE, 'r') as f:
                                other_pid = f.read().strip()
                            logger.error(f"Another bot instance appears to be running (PID: {other_pid})")
                        except:
                            logger.error("Another bot instance appears to be running")
                        lock_file_handle.close()
                        return False
                
                # Write PID to lock file
                lock_file_handle.write(str(os.getpid()))
                lock_file_handle.flush()
                logger.info(f"Created lock file: {LOCK_FILE}")
            except Exception as e:
                logger.error(f"Error with lock file: {e}")
                if lock_file_handle:
                    lock_file_handle.close()
                    lock_file_handle = None
                return False
        
        # Write current PID to lock file
        lock_file_handle.seek(0)
        lock_file_handle.write(str(os.getpid()))
        lock_file_handle.flush()
        
        # Also create a PID file for easier management
        with open('bot.pid', 'w') as f:
            f.write(str(os.getpid()))
            
        return True
    except Exception as e:
        logger.error(f"Error creating lock file: {e}")
        if lock_file_handle:
            lock_file_handle.close()
            lock_file_handle = None
        return False

def release_lock():
    """Release the exclusive lock on exit"""
    global lock_file_handle
    
    if lock_file_handle:
        try:
            if os.name == 'posix':
                fcntl.flock(lock_file_handle, fcntl.LOCK_UN)
            lock_file_handle.close()
            os.unlink(LOCK_FILE)
            logger.info(f"Released lock: {LOCK_FILE}")
        except Exception as e:
            logger.error(f"Error releasing lock: {e}")
    
    # Always remove PID file on exit
    try:
        if os.path.exists('bot.pid'):
            os.unlink('bot.pid')
    except:
        pass

def signal_handler(sig, frame):
    """Обробник сигналів для коректного завершення"""
    global running
    logger.info("Отримано сигнал завершення роботи. Зупиняємо бота...")
    running = False
    sys.exit(0)

# Встановлюємо обробники сигналів
signal.signal(signal.SIGINT, signal_handler)
signal.signal(signal.SIGTERM, signal_handler)

def check_bot_token():
    """Перевіряє наявність токену для бота"""
    try:
        # Спочатку перевіряємо змінну середовища
        bot_token = os.environ.get('BOT_TOKEN')
        if bot_token:
            # Check if this is a placeholder token
            if 'placeholder' in bot_token.lower() or 'replace_me' in bot_token.lower():
                logger.warning("BOT_TOKEN is set, but appears to be a placeholder. Bot may not function correctly.")
                # Still return True to attempt to run the bot
                return True
            return True
            
        # Потім перевіряємо налаштування в Django
        if hasattr(settings, 'BOT_TOKEN'):
            token = settings.BOT_TOKEN
            # Save to environment variable for child processes
            os.environ['BOT_TOKEN'] = token
            return bool(token)
            
        # Потім перевіряємо налаштування в БД
        try:
            bot_settings = BotSettings.objects.first()
            if bot_settings and bot_settings.bot_token:
                # Встановлюємо токен в змінну середовища
                token = bot_settings.bot_token
                os.environ['BOT_TOKEN'] = token
                # Check if this is a placeholder token
                if 'placeholder' in token.lower() or 'replace_me' in token.lower():
                    logger.warning("Token from database appears to be a placeholder. Bot may not function correctly.")
                return True
        except:
            pass
            
        # Якщо немає токену, перевіряємо в файлі config.py
        try:
            sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), 'tg_bot'))
            from tg_bot.config import TOKEN_BOT
            if TOKEN_BOT:
                # Save to environment variable for child processes
                os.environ['BOT_TOKEN'] = TOKEN_BOT
                # Check if this is a placeholder token
                if 'placeholder' in TOKEN_BOT.lower() or 'replace_me' in TOKEN_BOT.lower():
                    logger.warning("Token from config.py appears to be a placeholder. Bot may not function correctly.")
                return True
        except Exception as e:
            logger.warning(f"Failed to import from config.py: {e}")
            
        logger.warning("Не знайдено токен для Telegram бота")
        return False
    except Exception as e:
        logger.error(f"Помилка при перевірці токену бота: {e}")
        return False

def validate_bot_token():
    """Validates that the bot token is valid by attempting to connect to the Telegram API"""
    try:
        from aiogram import Bot
        
        async def check_token():
            try:
                token = os.environ.get('BOT_TOKEN', '')
                bot = Bot(token=token)
                me = await bot.get_me()
                logger.info(f"✅ Token validated successfully! Connected to @{me.username}")
                await bot.session.close()
                return True
            except Exception as e:
                logger.error(f"❌ Token validation failed: {e}")
                return False
        
        # Create a new event loop
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            return loop.run_until_complete(check_token())
        finally:
            loop.close()
    except Exception as e:
        logger.error(f"Error during token validation: {e}")
        return False

def print_token_instructions():
    """Prints instructions on how to set a valid bot token"""
    print("\n===== TELEGRAM BOT TOKEN ISSUE =====")
    print("The current bot token is invalid or not set properly.")
    print("To fix this issue:")
    print("1. Run: python fix_token.py")
    print("   This utility will help you set a valid token.")
    print("2. Or set a valid token in one of these locations:")
    print("   - tg_bot/config.py (TOKEN_BOT variable)")
    print("   - Environment variable BOT_TOKEN")
    print("   - Database (BotSettings model)")
    print("=================================\n")
    
def start_bot():
    """Запускає Telegram бота"""
    logger.info("Запускаємо Telegram бота...")
    
    # Перевіряємо наявність токену
    if not check_bot_token():
        logger.warning("Немає токену для Telegram бота. Бот не запущено.")
        print_token_instructions()
        return False
    
    # Validate the token (but continue even if invalid)
    if not validate_bot_token():
        logger.warning("Недійсний токен для Telegram бота. Спроба запуску все одно...")
        print_token_instructions()
        # Continue anyway to attempt to run the bot
    
    try:
        # Метод 1: Запуск через імпорт і асинхронний запуск
        import asyncio
        from tg_bot.bot import main
        
        try:
            # Create a separate process for the bot to keep it running
            import subprocess
            
            # Run the bot in a new process so it doesn't block this script
            bot_process = subprocess.Popen(
                [sys.executable, '-c', 'import asyncio; import os; os.environ["BOT_TOKEN"]="' + os.environ.get('BOT_TOKEN', '') + '"; from tg_bot.bot import main; asyncio.run(main())'],
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                env=os.environ.copy()  # Pass all environment variables
            )
            
            # Check if process started properly
            if bot_process.poll() is None:
                logger.info(f"Bot успішно запущено в окремому процесі (PID: {bot_process.pid})")
                
                # Give it a moment to initialize
                time.sleep(5)
                
                # Check again if it's still running after 5 seconds
                if bot_process.poll() is None:
                    logger.info("Bot продовжує працювати після 5 секунд ініціалізації")
                    return True
                else:
                    return_code = bot_process.poll()
                    output, _ = bot_process.communicate()
                    logger.error(f"Bot завершився передчасно з кодом {return_code}. Вивід: {output.decode('utf-8', errors='ignore')}")
            else:
                logger.error("Bot не запустився належним чином")
                return False
                
        except Exception as e:
            logger.error(f"Помилка запуску бота через asyncio: {e}")
            # Продовжуємо до наступного методу
    except ImportError:
        logger.warning("Не вдалося імпортувати бота напряму, використовуємо альтернативний метод")
    
    # Метод 2: Запуск через підпроцес
    try:
        logger.info("Запускаємо бота через підпроцес")
        bot_script = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'tg_bot', 'bot.py')
        
        # Run the bot script in a persistent way
        bot_process = subprocess.Popen(
            [sys.executable, bot_script],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            env=os.environ.copy()  # Pass all environment variables
        )
        
        # Check if process started properly
        if bot_process.poll() is None:
            logger.info(f"Bot успішно запущено через підпроцес (PID: {bot_process.pid})")
            
            # Give it a moment to initialize
            time.sleep(5)
            
            # Check again if it's still running after 5 seconds
            if bot_process.poll() is None:
                logger.info("Bot продовжує працювати після 5 секунд ініціалізації")
                return True
            else:
                return_code = bot_process.poll()
                output, _ = bot_process.communicate()
                logger.error(f"Bot завершився передчасно з кодом {return_code}. Вивід: {output.decode('utf-8', errors='ignore')}")
        else:
            logger.error("Bot не запустився належним чином")
            return False
            
    except Exception as e:
        logger.error(f"Помилка запуску бота через підпроцес: {e}")
        logger.error(traceback.format_exc())
        return False

def main():
    """Основна функція запуску з повторними спробами"""
    logger.info("Запуск Telegram бота")
    
    # Отримуємо URL для налаштування
    public_url = os.environ.get('PUBLIC_URL', '')
    if public_url:
        logger.info(f"Виявлено PUBLIC_URL: {public_url}")
    
    # Цикл з повторними спробами
    retry_count = 0
    
    while running and retry_count < MAX_RETRIES:
        try:
            logger.info(f"Спроба запуску бота #{retry_count + 1}")
            success = start_bot()
            
            if success:
                logger.info("Бот успішно запущено")
                break
            else:
                retry_count += 1
                logger.warning(f"Не вдалося запустити бота. Спроба {retry_count}/{MAX_RETRIES}")
                time.sleep(RETRY_INTERVAL)
        except Exception as e:
            retry_count += 1
            logger.error(f"Непередбачена помилка: {e}")
            logger.error(traceback.format_exc())
            time.sleep(RETRY_INTERVAL)
    
    if retry_count >= MAX_RETRIES:
        logger.error("Досягнуто максимальну кількість спроб. Бот не запущено.")
    
    # Якщо запуск не вдався, продовжуємо роботу для підтримки веб-сервера
    while running:
        try:
            time.sleep(60)
            logger.info("Бот працює у фоновому режимі...")
        except KeyboardInterrupt:
            break

# Try to import with retry logic
max_retries = 3
retry_delay = 2  # seconds

def import_with_retry(max_attempts=max_retries, delay=retry_delay):
    """Import bot modules with retry logic"""
    attempt = 0
    last_error = None
    
    while attempt < max_attempts:
        try:
            # First try direct import
            try:
                # Import all components directly using __all__
                from tg_bot.bot import main, bot, dp
                logger.info("Successfully imported bot components directly")
                return main, bot, dp
            except ImportError as direct_error:
                logger.warning(f"Direct import failed: {direct_error}, trying module-level import")
                # Try alternative import
                import tg_bot.bot
                if hasattr(tg_bot.bot, 'main') and hasattr(tg_bot.bot, 'bot') and hasattr(tg_bot.bot, 'dp'):
                    logger.info("Successfully imported components via module")
                    return tg_bot.bot.main, tg_bot.bot.bot, tg_bot.bot.dp
                else:
                    raise ImportError(f"Bot module does not have required attributes: {dir(tg_bot.bot)}")
        except Exception as e:
            attempt += 1
            last_error = e
            logger.warning(f"Import attempt {attempt} failed: {e}")
            time.sleep(delay)
    
    # If we get here, all attempts failed
    logger.error(f"Failed to import bot modules after {max_attempts} attempts. Last error: {last_error}")
    raise last_error

async def setup_bot_commands(bot, commands=None):
    """Set up bot commands"""
    try:
        # Import needed classes
        from aiogram.types import BotCommand, BotCommandScopeDefault
        
        # Use default commands if none provided
        if not commands:
            commands = [
                BotCommand(command="start", description="Start the bot and show main menu"),
                BotCommand(command="menu", description="Show the main menu"),
                BotCommand(command="help", description="Show help information"),
                BotCommand(command="authorize", description="Start authorization process")
            ]
        
        # Set commands
        await bot.set_my_commands(commands=commands, scope=BotCommandScopeDefault())
        logger.info("Bot commands registered successfully")
    except Exception as e:
        logger.error(f"Error setting up bot commands: {e}")

async def run():
    try:
        # Import main function with retry
        main, bot, dp = import_with_retry()
        
        # Set up default commands
        commands = [
            {"command": "start", "description": "Start the bot and show main menu"},
            {"command": "menu", "description": "Show the main menu"},
            {"command": "help", "description": "Show help information"},
            {"command": "authorize", "description": "Start authorization process"}
        ]
        
        try:
            await setup_bot_commands(bot, commands)
        except Exception as cmd_error:
            logger.error(f"Error setting bot commands: {cmd_error}")
        
        # Run the bot
        logger.info("Starting the bot")
        await main()
    except Exception as e:
        logger.error(f"Error in run_bot.py: {e}")
        logger.error(traceback.format_exc())
        if "Bad Request: can't parse entities" in str(e):
            logger.error("Possible message formatting issue. Check message text for valid markup.")
        raise

# Kill any existing bot processes before starting a new one
def kill_existing_bot_processes():
    """Kill any existing bot processes to prevent conflicts"""
    try:
        # Different commands for different OS
        if os.name == 'nt':  # Windows
            # Find python processes running run_bot.py except current one
            current_pid = os.getpid()
            result = subprocess.run(
                ['tasklist', '/FI', 'IMAGENAME eq python.exe', '/FO', 'CSV'],
                capture_output=True,
                text=True
            )
            
            for line in result.stdout.splitlines()[1:]:  # Skip header
                if 'python.exe' in line and 'run_bot.py' in line:
                    try:
                        pid = int(line.split(',')[1].strip('"'))
                        if pid != current_pid:
                            logger.info(f"Killing existing bot process with PID {pid}")
                            os.kill(pid, signal.SIGTERM)
                    except (ValueError, IndexError):
                        pass
        else:  # Linux/Unix
            command = "ps -ef | grep 'python.*run_bot.py' | grep -v grep | awk '{print $2}'"
            result = subprocess.run(command, shell=True, capture_output=True, text=True)
            
            current_pid = os.getpid()
            for pid_str in result.stdout.splitlines():
                try:
                    pid = int(pid_str.strip())
                    if pid != current_pid:
                        logger.info(f"Killing existing bot process with PID {pid}")
                        os.kill(pid, signal.SIGTERM)
                except (ValueError, ProcessLookupError):
                    pass
        
        # Wait a bit for processes to terminate
        time.sleep(2)
        logger.info("Existing bot processes terminated")
    except Exception as e:
        logger.error(f"Error killing existing bot processes: {e}")

# Define the setup_django function that's being called but doesn't exist
def setup_django():
    """Initialize Django environment"""
    try:
        os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
        django.setup()
        logger.info("Django successfully initialized")
        return True
    except Exception as e:
        logger.error(f"Django initialization failed: {e}")
        logger.error(traceback.format_exc())
        return False

if __name__ == "__main__":
    try:
        # Kill any existing bot processes first
        kill_existing_bot_processes()
        
        # Try to acquire lock - exit if another instance is running
        if not acquire_lock():
            logger.error("Another bot instance is already running. Exiting.")
            sys.exit(1)
            
        # Initialize Django
        if not setup_django():
            release_lock()
            sys.exit(1)
        
        # Write process ID to file for management
        with open('bot.pid', 'w') as f:
            f.write(str(os.getpid()))
        
        # Import bot components - do this after Django setup
        try:
            from tg_bot.bot import main as bot_main
            from tg_bot.config import Config, load_config
            
            # Run the bot
            bot_main()
        except ImportError:
            # Alternative import path
            try:
                from tg_bot.launcher import main as bot_main
                bot_main()
                logger.info("Successfully imported bot components directly")
            except ImportError as e:
                logger.error(f"Error importing bot components: {e}")
                
                # Try a different approach
                try:
                    # Direct import from telethon worker
                    from tg_bot.telethon_worker import main as bot_main
                    bot_main()
                    logger.info("Successfully imported telethon worker")
                except ImportError as e:
                    logger.error(f"Failed to import any bot components: {e}")
                    release_lock()
                    sys.exit(1)
        except Exception as e:
            logger.error(f"Error running bot: {e}")
            logger.error(traceback.format_exc())
            release_lock()
            sys.exit(1)
    except KeyboardInterrupt:
        logger.info("Bot stopped by keyboard interrupt")
    except Exception as e:
        logger.error(f"Unhandled exception in run_bot.py: {e}")
        logger.error(traceback.format_exc())
    finally:
        # Always release the lock when exiting
        release_lock() 