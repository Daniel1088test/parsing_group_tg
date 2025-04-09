#!/usr/bin/env python3
"""
Standalone bot starter with minimal dependencies
This script directly runs the Telegram bot without using Django's async machinery
"""
import os
import sys
import time
import logging
import subprocess
import signal
import traceback
import io

# Fix for Windows console encoding issues with emoji
if sys.platform == 'win32':
    # Force UTF-8 output encoding when running on Windows
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='backslashreplace')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='backslashreplace')

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('direct_bot.log', encoding='utf-8'),
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
    """Ensure environment variables are set"""
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
    """Run the bot directly"""
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
    """Run a minimal emergency bot if the main bot fails"""
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
        
        # Create the full 4-button keyboard - explicit layout
        def get_full_keyboard():
            return types.ReplyKeyboardMarkup(
                keyboard=[
                    [types.KeyboardButton(text="📎 List of channels")],
                    [types.KeyboardButton(text="📍 Categories menu")],
                    [types.KeyboardButton(text="🌐 Go to the site")],
                    [types.KeyboardButton(text="🔑 Add new session")],
                ],
                resize_keyboard=True,
                is_persistent=True,
                input_field_placeholder="Виберіть опцію..."
            )
        
        # Register basic handlers
        @dp.message(Command("start"))
        async def cmd_start(message: types.Message):
            keyboard = get_full_keyboard()
            logger.info(f"Sending 4-button keyboard to user {message.from_user.id} on /start")
            await message.answer("Bot is running in emergency mode. Use the menu below:", reply_markup=keyboard)
        
        @dp.message(Command("menu"))
        async def cmd_menu(message: types.Message):
            keyboard = get_full_keyboard()
            logger.info(f"Sending 4-button keyboard to user {message.from_user.id} on /menu")
            await message.answer("Menu:", reply_markup=keyboard)
        
        # Special handler for button clicks
        @dp.message()
        async def all_messages(message: types.Message):
            text = message.text if message.text else ""
            logger.info(f"Received message from user {message.from_user.id}: {text}")
            
            # Always send the keyboard with any message
            keyboard = get_full_keyboard()
            
            # Different texts for different buttons
            if text in ["📎 List of channels", "List of channels"]:
                await message.answer("List of channels functionality (emergency mode)", reply_markup=keyboard)
            elif text in ["📍 Categories menu", "Categories menu"]:
                await message.answer("Categories menu functionality (emergency mode)", reply_markup=keyboard)
            elif text in ["🌐 Go to the site", "Go to the site"]:
                await message.answer("Website functionality (emergency mode)", reply_markup=keyboard)
            elif text in ["🔑 Add new session", "Add new session"]:
                await message.answer("Add session functionality (emergency mode)", reply_markup=keyboard)
            else:
                # For any other message, just send back the menu
                await message.answer("Please use the menu buttons below:", reply_markup=keyboard)
        
        async def main():
            # First check if we can connect to Telegram
            try:
                me = await bot.get_me()
                logger.info(f"Emergency bot connected as @{me.username}")
            except Exception as e:
                logger.error(f"Failed to connect emergency bot: {e}")
                return False
            
            # Setup proper shutdown
            async def shutdown():
                # Close the bot session
                if hasattr(bot, 'session') and hasattr(bot.session, 'close'):
                    if not bot.session.closed:
                        await bot.session.close()
                        logger.info("Bot session closed properly")
                
                # Explicitly close any aiohttp client sessions
                import aiohttp
                import asyncio
                import gc
                
                # Find and close all active aiohttp sessions
                for obj in gc.get_objects():
                    if isinstance(obj, aiohttp.ClientSession) and not obj.closed:
                        logger.info(f"Closing unclosed ClientSession: {obj!r}")
                        await obj.close()
            
            try:
                # Start polling
                logger.info("Starting emergency bot polling...")
                await dp.start_polling(bot)
                return True
            except Exception as e:
                logger.error(f"Error in emergency bot polling: {e}")
                return False
            finally:
                # Always ensure session is closed
                await shutdown()
        
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
