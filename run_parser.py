#!/usr/bin/env python3
"""
Запускає Telegram-парсер у фоновому режимі.
Обробляє помилки для стабільної роботи в Railway.
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
logger = logging.getLogger('parser_launcher')

# Ініціалізація Django
import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()

# Імпорт моделей Django
from admin_panel.models import TelegramSession, Channel, Category, Message
from django.conf import settings

# Змінні для управління роботою
RETRY_INTERVAL = 60  # секунди між спробами перезапуску
MAX_RETRIES = 5      # максимальна кількість спроб перезапуску
running = True

def signal_handler(sig, frame):
    """Обробник сигналів для коректного завершення"""
    global running
    logger.info("Отримано сигнал завершення роботи. Зупиняємо парсер...")
    running = False
    sys.exit(0)

# Встановлюємо обробники сигналів
signal.signal(signal.SIGINT, signal_handler)
signal.signal(signal.SIGTERM, signal_handler)

def check_sessions():
    """Перевіряє наявність активних сесій Telegram"""
    try:
        sessions = TelegramSession.objects.filter(is_active=True)
        return sessions.exists()
    except Exception as e:
        logger.error(f"Помилка при перевірці сесій: {e}")
        return False

def check_channels():
    """Перевіряє наявність активних каналів для парсингу"""
    try:
        channels = Channel.objects.filter(is_active=True)
        return channels.exists()
    except Exception as e:
        logger.error(f"Помилка при перевірці каналів: {e}")
        return False

def start_parser():
    """Запускає основний парсер Telegram"""
    logger.info("Запускаємо парсер повідомлень Telegram...")
    
    # Перевіряємо готовність системи
    if not check_sessions():
        logger.warning("Немає активних сесій Telegram. Парсер не запущено.")
        return False
        
    if not check_channels():
        logger.warning("Немає активних каналів для парсингу. Парсер не запущено.")
        return False
    
    try:
        # Імпортуємо і запускаємо основний парсер
        from telegram_parser.parser import TelegramParser
        
        parser = TelegramParser()
        parser.run()
        return True
    except ImportError:
        # Альтернативний метод - запуск через subprocess
        logger.info("Використовуємо альтернативний метод запуску через підпроцес")
        try:
            result = subprocess.run(
                ["python", "-m", "telegram_parser.main"],
                capture_output=True,
                text=True,
                check=False
            )
            
            if result.returncode != 0:
                logger.error(f"Парсер завершився з помилкою: {result.stderr}")
                return False
            else:
                logger.info("Парсер успішно запущено через підпроцес")
                return True
        except Exception as e:
            logger.error(f"Помилка запуску підпроцесу: {e}")
            return False
    except Exception as e:
        logger.error(f"Критична помилка при запуску парсера: {e}")
        logger.error(traceback.format_exc())
        return False

def main():
    """Основна функція запуску з повторними спробами"""
    logger.info("Запуск системи парсингу Telegram")
    
    # Отримуємо URL для налаштування
    public_url = os.environ.get('PUBLIC_URL', '')
    if public_url:
        logger.info(f"Виявлено PUBLIC_URL: {public_url}")
    
    # Цикл з повторними спробами
    retry_count = 0
    
    while running and retry_count < MAX_RETRIES:
        try:
            logger.info(f"Спроба запуску парсера #{retry_count + 1}")
            success = start_parser()
            
            if success:
                logger.info("Парсер успішно запущено")
                break
            else:
                retry_count += 1
                logger.warning(f"Не вдалося запустити парсер. Спроба {retry_count}/{MAX_RETRIES}")
                time.sleep(RETRY_INTERVAL)
        except Exception as e:
            retry_count += 1
            logger.error(f"Непередбачена помилка: {e}")
            logger.error(traceback.format_exc())
            time.sleep(RETRY_INTERVAL)
    
    if retry_count >= MAX_RETRIES:
        logger.error("Досягнуто максимальну кількість спроб. Парсер не запущено.")
    
    # Якщо запуск не вдався, продовжуємо роботу для підтримки веб-сервера
    while running:
        try:
            time.sleep(60)
            logger.info("Парсер працює у фоновому режимі...")
        except KeyboardInterrupt:
            break

if __name__ == "__main__":
    main()