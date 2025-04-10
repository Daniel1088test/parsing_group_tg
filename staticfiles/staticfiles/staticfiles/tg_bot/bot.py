import os
import django
import asyncio
import logging
from datetime import datetime
import sys
import traceback

# configuration of logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S',
)
logger = logging.getLogger('telegram_bot')

# Initialize Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
try:
    django.setup()
    logger.info("Django setup successful")
except Exception as e:
    logger.error(f"Django setup error: {e}")
    logger.error(traceback.format_exc())

def get_bot_token():
    """
    Отримання токену бота з різних джерел з перевіркою валідності
    """
    # 1. Спочатку перевіряємо змінну середовища з Railway
    token = os.environ.get('BOT_TOKEN')
    if token and len(token) > 30:  # Перевіряємо, що токен має достатню довжину
        logger.info(f"Використовуємо BOT_TOKEN з змінних середовища: {token[:8]}...")
        return token
        
    # 2. Спробуємо отримати з config.py
    try:
        from tg_bot.config import TOKEN_BOT
        if TOKEN_BOT and len(TOKEN_BOT) > 30:
            logger.info(f"Використовуємо TOKEN_BOT з config.py: {TOKEN_BOT[:8]}...")
            return TOKEN_BOT
    except ImportError:
        logger.warning("Не вдалося імпортувати TOKEN_BOT з config.py")
    
    # 3. Використаємо хардкодований токен як останній варіант
    hardcoded_token = "8102516142:AAFTsVXXujHHKoX2KZGqZXBHPBznfgh7kg0"
    logger.warning(f"Використання хардкодованого токену як резервний варіант: {hardcoded_token[:8]}...")
    return hardcoded_token

try:
    # Import required modules
    from aiogram import Bot, Dispatcher, types, F
    from aiogram.fsm.storage.memory import MemoryStorage
    from aiogram.filters import Command
    from tg_bot.middlewares import ChannelsDataMiddleware
    from tg_bot.handlers import common_router, admin_router, session_router

    # Get bot token and initialize
    TOKEN_BOT = get_bot_token()
    logger.info(f"Using bot token: {TOKEN_BOT[:8]}...")

    # Initialize bot and dispatcher
    bot = Bot(token=TOKEN_BOT)
    storage = MemoryStorage()
    dp = Dispatcher(storage=storage)
    
    # Add middleware
    dp.message.middleware(ChannelsDataMiddleware())
    dp.callback_query.middleware(ChannelsDataMiddleware())
    
    # Register routers
    dp.include_router(session_router)
    dp.include_router(admin_router)
    dp.include_router(common_router)
    
except Exception as e:
    logger.error(f"Error during bot initialization: {e}")
    logger.error(traceback.format_exc())
    # Create emergency bot if possible
    try:
        TOKEN_BOT = get_bot_token()
        bot = Bot(token=TOKEN_BOT)
        dp = Dispatcher()
        
        # Create emergency handler
        @dp.message(Command("start"))
        async def emergency_start(message: types.Message):
            await message.answer("Bot is running in emergency mode. Please contact the administrator.")
    except Exception as emergency_error:
        logger.critical(f"Failed to create emergency bot: {emergency_error}")
        bot = None
        dp = None

async def main():
    if bot is None or dp is None:
        logger.critical("Bot or dispatcher is None, cannot start!")
        return
        
    # display information about the bot start
    logger.info("====================================")
    logger.info(f"Bot started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    try:
        # Get bot info if possible
        try:
            bot_info = await bot.get_me()
            logger.info(f"Bot ID: {bot_info.id}")
            logger.info(f"Bot name: {bot_info.username}")
        except Exception as e:
            logger.error(f"Error getting bot info: {e}")
            logger.error("This usually means the bot token is invalid!")
            logger.error("Please check your BOT_TOKEN environment variable or config setting")
            return  # Exit early if we can't even get bot info
            
        logger.info("====================================")
        
        # delete all updates that came while the bot was offline
        try:
            await bot.delete_webhook(drop_pending_updates=True)
            logger.info("Old messages deleted")
        except Exception as e:
            logger.error(f"Error deleting webhook: {e}")
        
        # start polling
        logger.info("Starting to receive updates...")
        try:
            await dp.start_polling(bot, allowed_updates=dp.resolve_used_update_types())
        except Exception as e:
            logger.error(f"Error during bot operation: {e}")
            logger.error(traceback.format_exc())
    except Exception as e:
        logger.error(f"Critical error in main: {e}")
        logger.error(traceback.format_exc())
    finally:
        # Always attempt to close the bot session
        try:
            if bot and hasattr(bot, 'session') and not bot.session.closed:
                await bot.session.close()
                logger.info("Bot session closed")
        except Exception as close_error:
            logger.error(f"Error closing bot session: {close_error}")
        logger.info("Bot stopped") 