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
    from tg_bot.handlers import common_router, admin_router, session_router, session_buttons_router, menu_buttons_router, fallback_router
    from tg_bot.middlewares import ChannelsDataMiddleware
    
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
            
        # Якщо все невдало, повертаємо хардкодний токен (найгірший варіант)
        logger.error("Не вдалося знайти токен бота, використовуємо хардкодний токен")
        return "7923260865:AAGWm7t0Zz2PqFPI5PldEVwrOC4HZ_5oP0c"
    
    # initialize the bot and dispatcher
    TOKEN_BOT = get_bot_token()
    bot = Bot(token=TOKEN_BOT)
    storage = MemoryStorage()
    dp = Dispatcher(storage=storage)
    
    # add middleware for channel data
    dp.message.middleware(ChannelsDataMiddleware())
    dp.callback_query.middleware(ChannelsDataMiddleware())
    
    # register all routers
    dp.include_router(session_router)
    dp.include_router(session_buttons_router)
    dp.include_router(menu_buttons_router)
    dp.include_router(admin_router)
    dp.include_router(common_router)
    # Fallback router додаємо останнім, щоб він вловлював всі повідомлення, які не були оброблені іншими роутерами
    dp.include_router(fallback_router)
    
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