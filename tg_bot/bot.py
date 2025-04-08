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

from aiogram import Bot, Dispatcher, types
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.filters import Command
from aiogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton
from tg_bot.config import TOKEN_BOT, BOT_USERNAME, PUBLIC_URL
from tg_bot.handlers import common_router, admin_router, session_router

# initialize the bot and dispatcher
bot = Bot(token=TOKEN_BOT, parse_mode="HTML")
dp = Dispatcher(storage=MemoryStorage())

# register all routers
dp.include_router(session_router)
dp.include_router(admin_router)
dp.include_router(common_router)

@dp.message(Command('start'))
async def start_command(message: Message):
    """Handle the /start command"""
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="🌐 Відкрити сайт", url=PUBLIC_URL)]
        ]
    )
    
    welcome_text = (
        f"👋 Вітаю у {BOT_USERNAME}!\n\n"
        "Цей бот допомагає керувати та моніторити Telegram канали.\n"
        "Натисніть кнопку нижче, щоб відкрити веб-інтерфейс:"
    )
    
    await message.reply(
        welcome_text,
        reply_markup=keyboard
    )

async def main():
    try:
        # Delete webhook and drop pending updates
        await bot.delete_webhook(drop_pending_updates=True)
        
        # Get bot info
        me = await bot.get_me()
        logger.info("====================================")
        logger.info(f"Bot started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        logger.info(f"Bot ID: {me.id}")
        logger.info(f"Bot name: {me.username}")
        logger.info("====================================")
        
        # Start polling with aggressive settings
        logger.info("Starting to receive updates...")
        await dp.start_polling(
            bot,
            allowed_updates=["message", "callback_query"],
            polling_timeout=30,
            reset_webhook=True,
            delete_webhook=True,
            skip_updates=True
        )
    except Exception as e:
        logger.error(f"Error during bot operation: {e}")
        raise
    finally:
        logger.info("Bot stopped")
        if bot.session:
            await bot.session.close()

if __name__ == "__main__":
    asyncio.run(main()) 