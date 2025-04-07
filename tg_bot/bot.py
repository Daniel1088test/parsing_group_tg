import os
import django
import asyncio
import logging
from datetime import datetime

# configuration of logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S',
)
logger = logging.getLogger('telegram_bot')

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()

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