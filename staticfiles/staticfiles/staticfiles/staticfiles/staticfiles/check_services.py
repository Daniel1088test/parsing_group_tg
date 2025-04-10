#!/usr/bin/env python3
"""
Скрипт для перевірки та запуску всіх сервісів проекту
Налаштування бота, парсера та Django сервера
"""
import os
import sys
import time
import subprocess
import psutil
import logging
import signal
from datetime import datetime

# Налаштування логування
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('services_check.log')
    ]
)
logger = logging.getLogger('services_check')

# Ініціалізація Django
import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()

# Імпорт моделей Django
from admin_panel.models import BotSettings, TelegramSession, Channel

def check_processes(service_name):
    """Перевіряє, чи запущений процес з вказаною назвою"""
    for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
        try:
            cmdline = ' '.join(proc.info['cmdline']) if proc.info['cmdline'] else ''
            if service_name in cmdline:
                return proc.info['pid']
        except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
            pass
    return None

def check_bot_settings():
    """Перевіряє налаштування бота в базі даних"""
    try:
        bot_settings = BotSettings.objects.first()
        if not bot_settings:
            # Створюємо налаштування бота за замовчуванням
            bot_settings = BotSettings.objects.create(
                bot_username="Channels_hunt_bot",
                bot_name="Telegram Channel Parser",
                bot_token=os.environ.get('BOT_TOKEN', ''),
                default_api_id=os.environ.get('API_ID', '2496'),
                default_api_hash=os.environ.get('API_HASH', '')
            )
            logger.info("Створено налаштування бота за замовчуванням")
        
        # Оновлюємо токен бота, якщо він вказаний в змінних середовища
        if os.environ.get('BOT_TOKEN') and not bot_settings.bot_token:
            bot_settings.bot_token = os.environ.get('BOT_TOKEN')
            bot_settings.save()
            logger.info("Оновлено токен бота з змінних середовища")
            
        return bool(bot_settings.bot_token)
    except Exception as e:
        logger.error(f"Помилка при перевірці налаштувань бота: {e}")
        return False

def check_telegram_sessions():
    """Перевіряє наявність активних Telegram сесій"""
    try:
        count = TelegramSession.objects.filter(is_active=True).count()
        logger.info(f"Знайдено {count} активних Telegram сесій")
        return count > 0
    except Exception as e:
        logger.error(f"Помилка при перевірці Telegram сесій: {e}")
        return False

def check_channels():
    """Перевіряє наявність активних каналів для парсингу"""
    try:
        count = Channel.objects.filter(is_active=True).count()
        logger.info(f"Знайдено {count} активних каналів для парсингу")
        return count > 0
    except Exception as e:
        logger.error(f"Помилка при перевірці каналів: {e}")
        return False

def start_bot():
    """Запускає Telegram бота"""
    bot_script = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'run_bot.py')
    if not os.path.exists(bot_script):
        logger.error(f"Скрипт бота не знайдено: {bot_script}")
        return False
        
    try:
        # Робимо скрипт виконуваним
        os.chmod(bot_script, 0o755)
        
        # Запускаємо процес
        process = subprocess.Popen(
            [sys.executable, bot_script],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
        )
        
        logger.info(f"Бот запущено з PID: {process.pid}")
        return True
    except Exception as e:
        logger.error(f"Помилка при запуску бота: {e}")
        return False

def start_parser():
    """Запускає парсер повідомлень"""
    parser_script = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'run_parser.py')
    if not os.path.exists(parser_script):
        logger.error(f"Скрипт парсера не знайдено: {parser_script}")
        return False
        
    try:
        # Робимо скрипт виконуваним
        os.chmod(parser_script, 0o755)
        
        # Запускаємо процес
        process = subprocess.Popen(
            [sys.executable, parser_script],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
        )
        
        logger.info(f"Парсер запущено з PID: {process.pid}")
        return True
    except Exception as e:
        logger.error(f"Помилка при запуску парсера: {e}")
        return False

def main():
    """Головна функція скрипту"""
    logger.info("=== Перевірка та запуск сервісів ===")
    
    # Перевіряємо налаштування бота
    logger.info("Перевіряємо налаштування бота...")
    if not check_bot_settings():
        logger.warning("Токен бота не налаштовано в системі")
    
    # Перевіряємо запущені процеси
    bot_pid = check_processes('run_bot.py')
    parser_pid = check_processes('run_parser.py')
    
    # Перевіряємо та запускаємо бота, якщо треба
    if bot_pid:
        logger.info(f"Бот вже запущено (PID: {bot_pid})")
    else:
        logger.info("Запускаємо бота...")
        start_bot()
    
    # Перевіряємо сесії та канали перед запуском парсера
    has_sessions = check_telegram_sessions()
    has_channels = check_channels()
    
    # Перевіряємо та запускаємо парсер, якщо потрібно і є умови
    if parser_pid:
        logger.info(f"Парсер вже запущено (PID: {parser_pid})")
    elif has_sessions and has_channels:
        logger.info("Запускаємо парсер...")
        start_parser()
    else:
        if not has_sessions:
            logger.warning("Не знайдено активних Telegram сесій. Парсер не запущено.")
        if not has_channels:
            logger.warning("Не знайдено активних каналів для парсингу. Парсер не запущено.")
    
    logger.info("=== Перевірка завершена ===")

if __name__ == "__main__":
    main() 