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

# Налаштування логування
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger('bot_launcher')

# Ініціалізація Django
import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()

# Імпорт моделей Django
from admin_panel.models import BotSettings
from django.conf import settings

# Змінні для управління роботою
RETRY_INTERVAL = 30  # секунди між спробами перезапуску
MAX_RETRIES = 5      # максимальна кількість спроб перезапуску
running = True

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
        import asyncio
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

if __name__ == "__main__":
    main() 