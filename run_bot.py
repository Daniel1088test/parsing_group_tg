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
            return True
            
        # Потім перевіряємо налаштування в Django
        if hasattr(settings, 'BOT_TOKEN'):
            return bool(settings.BOT_TOKEN)
            
        # Потім перевіряємо налаштування в БД
        try:
            bot_settings = BotSettings.objects.first()
            if bot_settings and bot_settings.bot_token:
                # Встановлюємо токен в змінну середовища
                os.environ['BOT_TOKEN'] = bot_settings.bot_token
                return True
        except:
            pass
            
        # Якщо немає токену, перевіряємо в файлі config.py
        try:
            from tg_bot.config import TOKEN_BOT
            if TOKEN_BOT:
                return True
        except:
            pass
            
        logger.warning("Не знайдено токен для Telegram бота")
        return False
    except Exception as e:
        logger.error(f"Помилка при перевірці токену бота: {e}")
        return False

def start_bot():
    """Запускає Telegram бота"""
    logger.info("Запускаємо Telegram бота...")
    
    # Перевіряємо наявність токену
    if not check_bot_token():
        logger.warning("Немає токену для Telegram бота. Бот не запущено.")
        return False
    
    try:
        # Метод 1: Запуск через імпорт і асинхронний запуск
        import asyncio
        from tg_bot.bot import main
        
        try:
            asyncio.run(main())
            return True
        except Exception as e:
            logger.error(f"Помилка запуску бота через asyncio: {e}")
            # Продовжуємо до наступного методу
    except ImportError:
        logger.warning("Не вдалося імпортувати бота напряму, використовуємо альтернативний метод")
    
    # Метод 2: Запуск через підпроцес
    try:
        logger.info("Запускаємо бота через підпроцес")
        bot_script = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'tg_bot', 'bot.py')
        
        result = subprocess.run(
            [sys.executable, bot_script],
            capture_output=True,
            text=True,
            check=False
        )
        
        if result.returncode != 0:
            logger.error(f"Бот завершився з помилкою: {result.stderr}")
            return False
        else:
            logger.info("Бот успішно запущено через підпроцес")
            return True
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