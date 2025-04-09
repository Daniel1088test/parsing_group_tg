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
    from aiogram import Bot, Dispatcher, types, F
    from aiogram.fsm.storage.memory import MemoryStorage
    from aiogram.filters import Command
    from tg_bot.handlers import common_router, admin_router, session_router, session_buttons_router, menu_buttons_router, fallback_router
    from tg_bot.middlewares import ChannelsDataMiddleware, MenuInitMiddleware
    
    # Отримуємо токен бота з різних можливих джерел
    def get_bot_token():
        # 1. Спочатку перевіряємо змінну середовища
        token = os.environ.get('BOT_TOKEN')
        if token:
            logger.info("Використовуємо BOT_TOKEN з змінних середовища")
            return token
            
        # 2. Перевіряємо змінну з config.py
        try:
            from tg_bot.config import TOKEN_BOT
            if TOKEN_BOT:
                logger.info("Використовуємо TOKEN_BOT з config.py")
                return TOKEN_BOT
        except ImportError:
            logger.warning("Не вдалося імпортувати TOKEN_BOT з config.py")
            
        # 3. Перевіряємо налаштування Django
        try:
            from django.conf import settings
            if hasattr(settings, 'BOT_TOKEN') and settings.BOT_TOKEN:
                logger.info("Використовуємо BOT_TOKEN з налаштувань Django")
                return settings.BOT_TOKEN
        except:
            logger.warning("Не вдалося отримати токен з налаштувань Django")
            
        # 4. Намагаємося отримати з бази даних
        try:
            from admin_panel.models import BotSettings
            bot_settings = BotSettings.objects.first()
            if bot_settings and bot_settings.bot_token:
                logger.info("Використовуємо токен з бази даних")
                return bot_settings.bot_token
        except:
            logger.warning("Не вдалося отримати токен з бази даних")
            
        # 5. Railway deployment failsafe - use hardcoded token
        if os.environ.get('RAILWAY_SERVICE_NAME'):
            hardcoded_token = "7923260865:AAGYew9JnOJV6hz0LGeRCb1kS6AejHoX61g"
            logger.warning("Using hardcoded token for Railway deployment")
            return hardcoded_token
            
        # 6. Create a placeholder token and inform the user
        logger.error("Не вдалося знайти токен бота. Використовуємо тимчасовий токен")
        logger.error("⚠️ Для налаштування справжнього токену, виконайте python fix_token.py")
        return "placeholder_token_fix_me"
    
    # initialize the bot and dispatcher
    TOKEN_BOT = get_bot_token()
    
    # Check if this is a placeholder/invalid token
    if 'placeholder' in TOKEN_BOT.lower() or 'replace' in TOKEN_BOT.lower():
        logger.warning("⚠️ Using placeholder token. Bot will likely fail to connect to Telegram API")
        logger.warning("⚠️ Run 'python fix_token.py' to set a valid token")
    
    try:
        bot = Bot(token=TOKEN_BOT)
        storage = MemoryStorage()
        dp = Dispatcher(storage=storage)
        
        # add middleware for channel data and menu initialization
        dp.message.middleware(ChannelsDataMiddleware())
        dp.callback_query.middleware(ChannelsDataMiddleware())
        dp.message.middleware(MenuInitMiddleware())  # Add menu middleware
        
        # Add special command to force menu refresh
        @dp.message(Command("menu"))
        async def force_menu(message: types.Message):
            """Force show the menu keyboard"""
            from aiogram.types import ReplyKeyboardMarkup, KeyboardButton
            
            # Create a keyboard directly
            keyboard = ReplyKeyboardMarkup(
                keyboard=[
                    [KeyboardButton(text="📎 List of channels")],
                    [KeyboardButton(text="📍 Categories menu")],
                    [KeyboardButton(text="🌐 Go to the site")],
                    [KeyboardButton(text="🔑 Add new session")],
                ],
                resize_keyboard=True,
                is_persistent=True  # Make it persistent
            )
            
            await message.answer("Menu refreshed. You should see the buttons below:", reply_markup=keyboard)
        
        # Add a special handler for menu button text that directly relates to the buttons
        @dp.message(F.text.in_(["Show menu", "меню", "Меню", "menu", "Menu"]))
        async def handle_menu_text(message: types.Message):
            """Handle text requests for menu"""
            await force_menu(message)
        
        # register all routers
        dp.include_router(session_router)
        dp.include_router(session_buttons_router)
        dp.include_router(menu_buttons_router)
        dp.include_router(admin_router)
        dp.include_router(common_router)
        # Fallback router додаємо останнім, щоб він вловлював всі повідомлення, які не були оброблені іншими роутерами
        dp.include_router(fallback_router)
    except Exception as bot_init_error:
        logger.error(f"Failed to initialize bot: {bot_init_error}")
        logger.error("This is likely due to an invalid bot token.")
        logger.error("Please run 'python fix_token.py' to set a valid token")
        # Re-raise the exception to abort startup
        raise
    
    async def health_check():
        """
        Функція для перевірки здоров'я бота
        Повертає True, якщо бот працює нормально
        """
        try:
            # Перевіряємо, чи можемо отримати інформацію про бота
            bot_info = await bot.get_me()
            return {
                "status": "ok",
                "bot_id": bot_info.id,
                "bot_name": bot_info.username,
                "timestamp": datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            }
        except Exception as e:
            logger.error(f"Health check failed: {e}")
            return {
                "status": "error",
                "error": str(e),
                "timestamp": datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            }
    
    async def main():
        # display information about the bot start
        logger.info("====================================")
        logger.info(f"Bot started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        
        try:
            bot_info = await bot.get_me()
            logger.info(f"Bot ID: {bot_info.id}")
            logger.info(f"Bot name: {bot_info.username}")
        except Exception as e:
            logger.error(f"Error getting bot info: {e}")
            logger.error("Bot token may be invalid! Please check your configuration.")
            return
        
        logger.info("====================================")
        
        # delete all updates that came while the bot was offline
        try:
            await bot.delete_webhook(drop_pending_updates=True)
            logger.info("Old messages deleted")
        except Exception as e:
            logger.error(f"Error deleting webhook: {e}")
        
        # We don't need to re-register the /start command as it's already in common_router
        # This was overriding the proper handler with a simplified version without keyboard
        
        # start polling
        logger.info("Starting to receive updates...")
        try:
            # Make sure we're using long polling to stay connected
            await dp.start_polling(
                bot, 
                allowed_updates=dp.resolve_used_update_types(),
                polling_timeout=60,  # Longer timeout to maintain connection
                handle_signals=False  # Let the parent process handle signals
            )
        except Exception as e:
            logger.error(f"Error during bot operation: {e}")
            import traceback
            logger.error(traceback.format_exc())
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