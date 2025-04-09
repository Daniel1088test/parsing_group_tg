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

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('direct_bot.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger('direct_bot')

def signal_handler(sig, frame):
    logger.info(f"Received signal {sig}, shutting down...")
    sys.exit(0)

signal.signal(signal.SIGINT, signal_handler)
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

def create_health_checks():
    """Create health check endpoints"""
    for file in ['health.txt', 'healthz.txt', 'health.html', 'healthz.html']:
        try:
            with open(file, 'w') as f:
                f.write('ok')
            logger.info(f"Created health check file: {file}")
        except Exception as e:
            logger.error(f"Error creating health check file {file}: {e}")

def run_bot():
    """Run the bot directly using subprocess"""
    try:
        logger.info("Starting the bot process...")
        
        # Create log directory if it doesn't exist
        os.makedirs('logs/bot', exist_ok=True)
        
        # Start the bot process
        proc = subprocess.Popen(
            [sys.executable, 'run_bot.py'],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            universal_newlines=True,
            bufsize=1  # Line buffered
        )
        
        # Print the PID
        logger.info(f"Bot started with PID: {proc.pid}")
        
        # Save PID to file
        with open('direct_bot.pid', 'w') as f:
            f.write(str(proc.pid))
        
        # Monitor the process output
        for line in proc.stdout:
            sys.stdout.write(line)
            logger.info(line.strip())
        
        # Wait for the process to complete
        return_code = proc.wait()
        logger.error(f"Bot process exited with code {return_code}")
        return return_code
    except Exception as e:
        logger.error(f"Error running bot: {e}")
        logger.error(traceback.format_exc())
        return 1

def run_emergency_direct():
    """Run the bot using direct aiogram import without Django"""
    try:
        logger.info("Starting emergency direct bot operation...")
        
        # Import aiogram and other dependencies
        from aiogram import Bot, Dispatcher
        from aiogram.types import BotCommand, BotCommandScopeDefault, Message, ReplyKeyboardMarkup, KeyboardButton
        from aiogram.filters import Command
        
        # Get bot token
        token = os.environ.get('BOT_TOKEN')
        if not token:
            logger.error("No BOT_TOKEN found in environment!")
            return 1
        
        # Initialize bot and dispatcher
        bot = Bot(token=token)
        dp = Dispatcher()
        
        # Register command handlers
        @dp.message(Command("start"))
        async def cmd_start(message: Message):
            """Start command handler"""
            keyboard = ReplyKeyboardMarkup(
                keyboard=[
                    [KeyboardButton(text="📎 List of channels")],
                    [KeyboardButton(text="📍 Categories menu")],
                    [KeyboardButton(text="🌐 Go to the site")],
                    [KeyboardButton(text="🔑 Add new session")],
                ],
                resize_keyboard=True,
                is_persistent=True
            )
            await message.answer("Welcome to the Channel Parser Bot. Use the menu below:", reply_markup=keyboard)
        
        @dp.message(Command("menu"))
        async def cmd_menu(message: Message):
            """Menu command handler"""
            keyboard = ReplyKeyboardMarkup(
                keyboard=[
                    [KeyboardButton(text="📎 List of channels")],
                    [KeyboardButton(text="📍 Categories menu")],
                    [KeyboardButton(text="🌐 Go to the site")],
                    [KeyboardButton(text="🔑 Add new session")],
                ],
                resize_keyboard=True,
                is_persistent=True
            )
            await message.answer("Here's the menu:", reply_markup=keyboard)
        
        async def set_bot_commands():
            """Set up bot commands"""
            commands = [
                BotCommand(command="start", description="Start the bot and show main menu"),
                BotCommand(command="menu", description="Show the main menu"),
                BotCommand(command="help", description="Show help"),
            ]
            try:
                await bot.set_my_commands(commands=commands, scope=BotCommandScopeDefault())
                logger.info("Bot commands registered successfully")
            except Exception as e:
                logger.error(f"Error setting bot commands: {e}")
        
        async def main():
            """Main function"""
            try:
                # Get bot info
                bot_info = await bot.get_me()
                logger.info(f"Bot connected: @{bot_info.username} (ID: {bot_info.id})")
                
                # Create verification flag
                with open('bot_verified.flag', 'w') as f:
                    f.write(f"{bot_info.id}:{bot_info.username}")
                logger.info("Created bot verification flag")
                
                # Set up commands
                await set_bot_commands()
                
                # Start long polling
                logger.info("Starting polling...")
                await dp.start_polling(bot)
            except Exception as e:
                logger.error(f"Error in main function: {e}")
                logger.error(traceback.format_exc())
        
        # Run the bot
        import asyncio
        logger.info("Running emergency direct bot...")
        asyncio.run(main())
        
        return 0
    except Exception as e:
        logger.error(f"Error running emergency direct bot: {e}")
        logger.error(traceback.format_exc())
        return 1

if __name__ == "__main__":
    logger.info("=== Direct Bot Starter ===")
    
    # Check environment
    check_environment()
    
    # Create health check files
    create_health_checks()
    
    # Create necessary directories
    os.makedirs('logs/bot', exist_ok=True)
    os.makedirs('media/messages', exist_ok=True)
    os.makedirs('staticfiles/media', exist_ok=True)
    
    try:
        # First try standard bot launch
        logger.info("Attempting standard bot launch...")
        exit_code = run_bot()
        
        # If that fails, try emergency direct method
        if exit_code != 0:
            logger.warning("Standard bot launch failed, trying emergency direct method...")
            exit_code = run_emergency_direct()
        
        # Exit with the appropriate code
        sys.exit(exit_code)
    except KeyboardInterrupt:
        logger.info("Interrupted by user")
        sys.exit(0)
    except Exception as e:
        logger.error(f"Unhandled exception: {e}")
        logger.error(traceback.format_exc())
        sys.exit(1) 