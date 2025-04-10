#!/usr/bin/env python3
"""
Emergency Fix Script for Telegram Bot
This script addresses several critical issues with the bot:
1. Database schema issues (missing columns)
2. Bot import problems
3. Creates necessary health check files
"""
import os
import sys
import django
import traceback
import logging
import asyncio
import io

# Fix for Windows console encoding issues with emoji
if sys.platform == 'win32':
    # Force UTF-8 output encoding when running on Windows
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='backslashreplace')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='backslashreplace')

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('emergency_fix.log', encoding='utf-8'),
        logging.StreamHandler(sys.stdout)  # Use sys.stdout to fix encoding issues
    ]
)
logger = logging.getLogger('emergency_fix')

def ensure_environment():
    """Ensure environment variables are set correctly"""
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
    
    # Ensure BOT_TOKEN is available
    token = os.environ.get('BOT_TOKEN')
    if not token:
        # Try to get from various sources
        if os.path.exists('bot_token.env'):
            try:
                with open('bot_token.env', 'r') as f:
                    content = f.read().strip()
                    if content.startswith('BOT_TOKEN='):
                        token = content.split('=', 1)[1].strip()
                        os.environ['BOT_TOKEN'] = token
                        logger.info("Loaded BOT_TOKEN from bot_token.env")
            except Exception as e:
                logger.error(f"Error reading bot_token.env: {e}")
        
        if not token:
            try:
                from tg_bot.config import TOKEN_BOT
                if TOKEN_BOT:
                    os.environ['BOT_TOKEN'] = TOKEN_BOT
                    logger.info("Loaded BOT_TOKEN from config.py")
                    token = TOKEN_BOT
            except Exception as e:
                logger.error(f"Error loading from config.py: {e}")
        
        if not token:
            # Hardcoded token as last resort
            token = "7923260865:AAGYew9JnOJV6hz0LGeRCb1kS6AejHoX61g"
            os.environ['BOT_TOKEN'] = token
            logger.warning("Using hardcoded token as fallback")
            
            # Save it to file for consistency
            with open('bot_token.env', 'w') as f:
                f.write(f"BOT_TOKEN={token}")
    
    return True

def fix_database():
    """Fix database schema and settings"""
    try:
        # Initialize Django
        django.setup()
        
        from django.db import connection, OperationalError
        
        # Check for Railway DATABASE_URL
        is_railway = bool(os.environ.get('RAILWAY_SERVICE_NAME'))
        has_database_url = bool(os.environ.get('DATABASE_URL'))
        
        if is_railway and has_database_url:
            logger.info("Running on Railway with DATABASE_URL")
            os.environ['USE_POSTGRES'] = 'True'
        
        # Detect database type
        db_engine = connection.vendor
        logger.info(f"Using {db_engine} database")
        
        # Check connection
        try:
            with connection.cursor() as cursor:
                cursor.execute("SELECT 1")
                logger.info("Database connection verified")
        except OperationalError as e:
            logger.error(f"Database connection error: {e}")
            return False
        
        # Fix BotSettings table
        try:
            with connection.cursor() as cursor:
                # Check if BotSettings table exists - SQLite compatible query
                if db_engine == 'sqlite':
                    cursor.execute("""
                        SELECT name FROM sqlite_master 
                        WHERE type='table' AND name='admin_panel_botsettings'
                    """)
                    table_exists = cursor.fetchone() is not None
                else:
                    # PostgreSQL query
                    cursor.execute("""
                        SELECT EXISTS (
                            SELECT 1 FROM information_schema.tables 
                            WHERE table_name='admin_panel_botsettings'
                        )
                    """)
                    table_exists = cursor.fetchone()[0]
                
                if table_exists:
                    logger.info("BotSettings table exists")
                    
                    # Check for bot_name column - SQLite compatible way
                    if db_engine == 'sqlite':
                        cursor.execute("PRAGMA table_info(admin_panel_botsettings)")
                        columns = cursor.fetchall()
                        column_exists = any(col[1] == 'bot_name' for col in columns)
                    else:
                        # PostgreSQL query
                        cursor.execute("""
                            SELECT EXISTS (
                                SELECT 1 FROM information_schema.columns 
                                WHERE table_name='admin_panel_botsettings' AND column_name='bot_name'
                            )
                        """)
                        column_exists = cursor.fetchone()[0]
                    
                    if not column_exists:
                        logger.info("Adding missing bot_name column")
                        cursor.execute("""
                            ALTER TABLE admin_panel_botsettings 
                            ADD COLUMN bot_name VARCHAR(255) NULL
                        """)
                        connection.commit()
                else:
                    logger.info("Creating BotSettings table")
                    # Different SQL for PostgreSQL vs SQLite
                    if db_engine == 'postgresql':
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
                    else:
                        cursor.execute("""
                            CREATE TABLE admin_panel_botsettings (
                                id INTEGER PRIMARY KEY AUTOINCREMENT,
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
                    connection.commit()
                
                # Check if we need to create settings
                cursor.execute("SELECT COUNT(*) FROM admin_panel_botsettings")
                count = cursor.fetchone()[0]
                
                if count == 0:
                    logger.info("Adding default settings to BotSettings")
                    token = os.environ.get('BOT_TOKEN')
                    # Different parameter placeholders for PostgreSQL vs SQLite
                    if db_engine == 'postgresql':
                        cursor.execute("""
                            INSERT INTO admin_panel_botsettings 
                            (bot_token, bot_username, bot_name, menu_style, default_api_id, 
                            polling_interval, max_messages_per_channel)
                            VALUES (%s, %s, %s, %s, %s, %s, %s)
                        """, [
                            token, 'Channels_hunt_bot', 'Channel Parser Bot', 'default', 
                            2496, 30, 10
                        ])
                    else:
                        cursor.execute("""
                            INSERT INTO admin_panel_botsettings 
                            (bot_token, bot_username, bot_name, menu_style, default_api_id, 
                            polling_interval, max_messages_per_channel)
                            VALUES (?, ?, ?, ?, ?, ?, ?)
                        """, [
                            token, 'Channels_hunt_bot', 'Channel Parser Bot', 'default', 
                            2496, 30, 10
                        ])
                    connection.commit()
            
            logger.info("Database fixes completed successfully")
            return True
        except Exception as e:
            logger.error(f"Error fixing database schema: {e}")
            logger.error(traceback.format_exc())
            return False
            
    except Exception as e:
        logger.error(f"Database setup error: {e}")
        logger.error(traceback.format_exc())
        return False

def fix_bot_imports():
    """Ensure proper bot imports are defined"""
    try:
        bot_file = 'tg_bot/bot.py'
        
        if os.path.exists(bot_file):
            with open(bot_file, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Check if __all__ already exists
            if '__all__' not in content:
                # Find where to insert __all__
                if 'async def heartbeat_task():' in content:
                    # Split content at heartbeat_task
                    parts = content.split('async def heartbeat_task():')
                    if len(parts) >= 2:
                        # Split second part at if __name__
                        end_parts = parts[1].split('if __name__ ==')
                        if len(end_parts) >= 2:
                            # Reassemble with __all__ added
                            new_content = parts[0] + 'async def heartbeat_task():' + end_parts[0]
                            new_content += '\n    # Export the main components for other modules to import\n'
                            new_content += '    __all__ = ["main", "bot", "dp"]\n    \n'
                            new_content += 'if __name__ ==' + end_parts[1]
                            
                            # Write back to file
                            with open(bot_file, 'w', encoding='utf-8') as f:
                                f.write(new_content)
                            
                            logger.info(f"Added __all__ to {bot_file}")
                        else:
                            logger.warning("Could not find 'if __name__' section")
                    else:
                        logger.warning("Could not properly split the file content")
                else:
                    logger.warning("Could not find heartbeat_task function")
            else:
                logger.info("__all__ already defined in bot.py")
            
            # Fix the start command handler to ensure 4 buttons
            if "@dp.message(Command(\"start\"))" not in content:
                # Find a place to insert the start handler
                target = "dp.message.middleware(MenuInitMiddleware())"
                if target in content:
                    # Add direct start handler after middleware
                    start_handler = """
        # Special handler for start command to fix keyboard issues
        @dp.message(Command("start"))
        async def force_start(message: types.Message):
            \"\"\"Ensure the start command shows all 4 buttons\"\"\"
            try:
                # Create keyboard with all 4 buttons
                keyboard = types.ReplyKeyboardMarkup(
                    keyboard=[
                        [types.KeyboardButton(text="📎 List of channels")],
                        [types.KeyboardButton(text="📍 Categories menu")],
                        [types.KeyboardButton(text="🌐 Go to the site")],
                        [types.KeyboardButton(text="🔑 Add new session")],
                    ],
                    resize_keyboard=True,
                    is_persistent=True
                )
                
                # Send message with keyboard
                await message.answer(
                    "Привіт! Бот запущено. Використовуйте меню нижче:",
                    reply_markup=keyboard
                )
                logger.info(f"Start message with 4-button keyboard sent to user {message.from_user.id}")
            except Exception as e:
                logger.error(f"Error in direct start handler: {e}")
                try:
                    # Last resort keyboard
                    simple_keyboard = types.ReplyKeyboardMarkup(
                        keyboard=[
                            [types.KeyboardButton(text="📎 List of channels")],
                            [types.KeyboardButton(text="📍 Categories menu")],
                            [types.KeyboardButton(text="🌐 Go to the site")],
                            [types.KeyboardButton(text="🔑 Add new session")],
                        ],
                        resize_keyboard=True,
                        is_persistent=True
                    )
                    await message.answer("Меню бота:", reply_markup=simple_keyboard)
                except Exception as e2:
                    logger.error(f"Critical error in direct start handler: {e2}")
                    await message.answer("Використовуйте команду /menu")
        """
                    new_content = content.replace(target, target + start_handler)
                    with open(bot_file, 'w', encoding='utf-8') as f:
                        f.write(new_content)
                    logger.info("Added direct start handler to fix keyboard issues")
            else:
                logger.info("Direct start handler already exists")
            
            # Verify if has main function
            if 'async def main():' not in content:
                logger.error("No main function found in bot.py - this is critical!")
                return False
                
            return True
        else:
            logger.error(f"Bot file not found: {bot_file}")
            return False
    except Exception as e:
        logger.error(f"Error fixing bot imports: {e}")
        logger.error(traceback.format_exc())
        return False

def create_health_checks():
    """Create health check files for monitoring"""
    try:
        for filename in ['health.txt', 'healthz.txt', 'health.html', 'healthz.html']:
            with open(filename, 'w') as f:
                f.write('ok')
            logger.info(f"Created health check file: {filename}")
        return True
    except Exception as e:
        logger.error(f"Error creating health check files: {e}")
        return False

def fix_direct_start_script():
    """Create or fix the direct start script"""
    script_path = 'direct_start_bot.py'
    script_content = """#!/usr/bin/env python3
\"\"\"
Standalone bot starter with minimal dependencies
This script directly runs the Telegram bot without using Django's async machinery
\"\"\"
import os
import sys
import time
import logging
import subprocess
import signal
import traceback

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('direct_bot.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger('direct_bot_starter')

def signal_handler(sig, frame):
    logger.info(f"Received signal {sig}, shutting down...")
    sys.exit(0)

# Register signal handlers if on Unix
if hasattr(signal, "SIGINT"):
    signal.signal(signal.SIGINT, signal_handler)
if hasattr(signal, "SIGTERM"):
    signal.signal(signal.SIGTERM, signal_handler)

def check_environment():
    \"\"\"Ensure environment variables are set\"\"\"
    token = os.environ.get('BOT_TOKEN')
    if not token:
        # Try to read from file
        if os.path.exists('bot_token.env'):
            try:
                with open('bot_token.env', 'r') as f:
                    content = f.read().strip()
                    if content.startswith('BOT_TOKEN='):
                        token = content.split('=', 1)[1].strip()
                        os.environ['BOT_TOKEN'] = token
                        logger.info("Loaded BOT_TOKEN from bot_token.env")
            except Exception as e:
                logger.error(f"Error reading bot_token.env: {e}")
        
        # Still no token? Try config.py
        if not token:
            try:
                sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
                from tg_bot.config import TOKEN_BOT
                if TOKEN_BOT:
                    os.environ['BOT_TOKEN'] = TOKEN_BOT
                    logger.info("Loaded BOT_TOKEN from config.py")
            except Exception as e:
                logger.error(f"Error loading token from config.py: {e}")
        
        # Last resort - hardcoded token
        if not token:
            hardcoded_token = "7923260865:AAGYew9JnOJV6hz0LGeRCb1kS6AejHoX61g"
            os.environ['BOT_TOKEN'] = hardcoded_token
            logger.warning("Using hardcoded token as last resort")
    
    # Check if DJANGO_SETTINGS_MODULE is set
    if 'DJANGO_SETTINGS_MODULE' not in os.environ:
        os.environ['DJANGO_SETTINGS_MODULE'] = 'core.settings'
        logger.info("Set DJANGO_SETTINGS_MODULE to core.settings")
    
    return True

def run_bot():
    \"\"\"Run the bot directly\"\"\"
    try:
        logger.info("Starting the bot directly...")
        
        # Ensure path includes current directory
        sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
        
        # Verify Django setup
        import django
        os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
        django.setup()
        logger.info("Django setup completed")
        
        # Direct bot launch
        import asyncio
        
        # Create run coroutine
        async def run_async_bot():
            try:
                # First try direct import
                try:
                    from tg_bot.bot import main, bot, dp
                    logger.info("Successfully imported bot components")
                except ImportError:
                    # Try loading module and accessing attributes
                    logger.warning("Direct import failed, trying module-level import")
                    import tg_bot.bot
                    main = tg_bot.bot.main
                    bot = tg_bot.bot.bot
                    dp = tg_bot.bot.dp
                    logger.info("Successfully imported via module")
                
                # Run the main function
                logger.info("Starting bot main function")
                await main()
                return True
            except ImportError as e:
                logger.error(f"Critical error in bot: {e}")
                logger.error(traceback.format_exc())
                return False
            except Exception as e:
                logger.error(f"Error running bot: {e}")
                logger.error(traceback.format_exc())
                return False
        
        # Run the async function
        if asyncio.run(run_async_bot()):
            logger.info("Bot completed successfully")
            return 0
        else:
            logger.error("Bot failed to run")
            return 1
    except Exception as e:
        logger.error(f"Critical error in bot: {e}")
        logger.error(traceback.format_exc())
        return 1

def run_emergency_bot():
    \"\"\"Run a minimal emergency bot if the main bot fails\"\"\"
    try:
        logger.info("Starting emergency minimal bot...")
        
        import asyncio
        from aiogram import Bot, Dispatcher, types
        from aiogram.filters import Command
        
        # Get token
        token = os.environ.get('BOT_TOKEN')
        if not token:
            logger.error("No BOT_TOKEN available for emergency bot")
            return 1
        
        # Initialize bot and dispatcher
        bot = Bot(token=token)
        dp = Dispatcher()
        
        # Register basic handlers
        @dp.message(Command("start"))
        async def cmd_start(message: types.Message):
            await message.answer("Bot is running in emergency mode. Use /menu to see available commands.")
        
        @dp.message(Command("menu"))
        async def cmd_menu(message: types.Message):
            keyboard = types.ReplyKeyboardMarkup(
                keyboard=[
                    [types.KeyboardButton(text="📎 List of channels")],
                    [types.KeyboardButton(text="📍 Categories menu")],
                ],
                resize_keyboard=True,
                is_persistent=True
            )
            await message.answer("Emergency menu (limited functionality):", reply_markup=keyboard)
        
        async def main():
            # First check if we can connect to Telegram
            try:
                me = await bot.get_me()
                logger.info(f"Emergency bot connected as @{me.username}")
            except Exception as e:
                logger.error(f"Failed to connect emergency bot: {e}")
                return False
            
            # Start polling
            logger.info("Starting emergency bot polling...")
            await dp.start_polling(bot)
            return True
        
        # Run the bot
        if asyncio.run(main()):
            logger.info("Emergency bot running successfully")
            return 0
        else:
            logger.error("Emergency bot failed to start")
            return 1
        
    except Exception as e:
        logger.error(f"Critical error in emergency bot: {e}")
        logger.error(traceback.format_exc())
        return 1

if __name__ == "__main__":
    logger.info("=== Direct Bot Starter ===")
    
    # Check environment
    check_environment()
    
    # Create necessary directories
    os.makedirs('logs/bot', exist_ok=True)
    
    try:
        # First try the standard bot
        exit_code = run_bot()
        
        # If that fails, try emergency bot
        if exit_code != 0:
            logger.warning("Main bot failed, trying emergency bot")
            exit_code = run_emergency_bot()
        
        sys.exit(exit_code)
    except KeyboardInterrupt:
        logger.info("Interrupted by user")
        sys.exit(0)
    except Exception as e:
        logger.error(f"Unhandled exception: {e}")
        logger.error(traceback.format_exc())
        sys.exit(1)
"""

    try:
        with open(script_path, 'w', encoding='utf-8') as f:
            f.write(script_content)
        logger.info(f"Created direct_start_bot.py script")
        
        # Make executable on Unix-like systems
        try:
            os.chmod(script_path, 0o755)
        except:
            pass
            
        return True
    except Exception as e:
        logger.error(f"Error creating direct_start_bot.py: {e}")
        return False

def verify_bot_connection():
    """Verify that the bot can connect to Telegram API"""
    try:
        # Initialize Django
        django.setup()
        
        # Helper function to run in an isolated event loop with its own clean-up
        async def run_async_isolated(coro):
            try:
                return await coro
            finally:
                # Force closing all unclosed client sessions
                pending = asyncio.all_tasks()
                for task in pending:
                    task.cancel()
                    try:
                        await task
                    except asyncio.CancelledError:
                        pass
                
                # This is a hack but ensures no unclosed sessions warning
                import gc
                import aiohttp
                for obj in gc.get_objects():
                    if isinstance(obj, aiohttp.ClientSession) and not obj.closed:
                        try:
                            await obj.close()
                        except:
                            pass
        
        async def check_connection():
            try:
                # Import the bot
                from tg_bot.bot import bot
                
                # Try to get bot info
                me = await bot.get_me()
                logger.info(f"Bot connection verified: @{me.username} (ID: {me.id})")
                return True
            except Exception as e:
                logger.error(f"Bot connection failed: {e}")
                logger.error(traceback.format_exc())
                return False
        
        # Run the check with strict isolation and cleanup
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            result = loop.run_until_complete(run_async_isolated(check_connection()))
        finally:
            loop.close()
            asyncio.set_event_loop(None)
            
        return result
    except Exception as e:
        logger.error(f"Error verifying bot connection: {e}")
        logger.error(traceback.format_exc())
        return False

def main():
    """Main function to execute all fixes"""
    logger.info("=== STARTING EMERGENCY BOT FIX ===")
    
    # Step 1: Set up environment
    logger.info("Setting up environment...")
    ensure_environment()
    
    # Step 2: Fix database
    logger.info("Fixing database schema...")
    db_fixed = fix_database()
    if db_fixed:
        logger.info("Database fixes completed successfully")
    else:
        logger.warning("Database fixes had issues, but continuing...")
    
    # Step 3: Fix bot imports
    logger.info("Fixing bot imports...")
    imports_fixed = fix_bot_imports()
    if imports_fixed:
        logger.info("Bot imports fixed successfully")
    else:
        logger.warning("Bot import fixes had issues, but continuing...")
    
    # Step 4: Create health checks
    logger.info("Creating health check files...")
    create_health_checks()
    
    # Step 5: Fix direct start script
    logger.info("Creating direct start script...")
    fix_direct_start_script()
    
    # Step 6: Verify bot connection
    logger.info("Verifying bot connection...")
    connection_ok = verify_bot_connection()
    if connection_ok:
        logger.info("Bot connection verified successfully")
    else:
        logger.warning("Bot connection verification failed")
    
    logger.info("=== EMERGENCY BOT FIX COMPLETED ===")
    
    # Final assessment
    if db_fixed and imports_fixed and connection_ok:
        logger.info("All fixes were applied successfully!")
        return True
    else:
        logger.warning("Some fixes may not have been completely successful.")
        return False

if __name__ == "__main__":
    # Make sure current directory is in path
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    
    # Set up environment
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
    
    result = main()
    sys.exit(0 if result else 1) 