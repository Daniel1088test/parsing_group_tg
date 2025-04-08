import os
import django
import asyncio
import logging
from datetime import datetime
import sys

# configuration of logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S',
)
logger = logging.getLogger('telegram_bot')

# Додаємо поточну директорію до шляху Python
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Встановлюємо змінну середовища та ініціалізуємо Django
try:
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
    django.setup()
    logger.info("Django setup successful")
except Exception as e:
    logger.error(f"Django setup error: {e}")

try:
    # Імпортуємо необхідні модулі
    from aiogram import Bot, Dispatcher
    from aiogram.fsm.storage.memory import MemoryStorage
    from tg_bot.config import TOKEN_BOT
    from tg_bot.handlers import common_router, admin_router, session_router
    from tg_bot.middlewares import ChannelsDataMiddleware
    
    # initialize the bot and dispatcher
    bot = Bot(token=TOKEN_BOT)
    storage = MemoryStorage()
    dp = Dispatcher(storage=storage)
    
    # add middleware for channel data
    dp.message.middleware(ChannelsDataMiddleware())
    dp.callback_query.middleware(ChannelsDataMiddleware())
    
    # register all routers
    dp.include_router(session_router)
    dp.include_router(admin_router)
    dp.include_router(common_router)
    
    async def main():
        # display information about the bot start
        logger.info("====================================")
        logger.info(f"Bot started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        logger.info(f"Bot ID: {(await bot.get_me()).id}")
        logger.info(f"Bot name: {(await bot.get_me()).username}")
        logger.info("====================================")
        
        # delete all updates that came while the bot was offline
        await bot.delete_webhook(drop_pending_updates=True)
        logger.info("Old messages deleted")
        
        # start polling
        logger.info("Starting to receive updates...")
        try:
            await dp.start_polling(bot, allowed_updates=dp.resolve_used_update_types())
        except Exception as e:
            logger.error(f"Error during bot operation: {e}")
        finally:
            logger.info("Bot stopped")
    
    if __name__ == "__main__":
        try:
            # Правильний спосіб запуску асинхронної функції
            asyncio.run(main())
        except KeyboardInterrupt:
            logger.info("Bot stopped by keyboard interrupt")
        except Exception as e:
            logger.error(f"Failed to start bot: {e}")
            import traceback
            logger.error(traceback.format_exc())
            sys.exit(1)
except Exception as e:
    logger.error(f"Critical error in bot initialization: {e}")
    import traceback
    logger.error(traceback.format_exc()) 