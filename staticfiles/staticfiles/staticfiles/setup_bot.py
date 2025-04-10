#!/usr/bin/env python3
"""
Скрипт для швидкого налаштування бота та інших необхідних компонентів
Створює необхідні записи в БД якщо вони відсутні
"""
import os
import sys
import logging
import argparse
from datetime import datetime

# Налаштування логування
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger('setup_bot')

# Ініціалізація Django
import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()

# Імпорт моделей Django
from admin_panel.models import BotSettings, TelegramSession, Channel, Category
from django.contrib.auth.models import User

def setup_bot_settings(bot_token=None, bot_username=None, bot_name=None, api_id=None, api_hash=None):
    """Налаштовує бота в базі даних"""
    logger.info("Налаштування бота...")

    # Отримуємо або створюємо запис налаштувань бота
    try:
        bot_settings = BotSettings.objects.first()
        if not bot_settings:
            logger.info("Створення нових налаштувань бота...")
            bot_settings = BotSettings(
                bot_username=bot_username or "Channels_hunt_bot",
                bot_name=bot_name or "Telegram Channel Parser",
                bot_token=bot_token or os.environ.get('BOT_TOKEN', ''),
                default_api_id=api_id or os.environ.get('API_ID', '19840544'),
                default_api_hash=api_hash or os.environ.get('API_HASH', 'c839f28bad345082329ec086fca021fa')
            )
            bot_settings.save()
            logger.info("Налаштування бота створено успішно")
        else:
            # Оновлюємо налаштування, якщо вони передані
            updated = False
            if bot_token and not bot_settings.bot_token:
                bot_settings.bot_token = bot_token
                updated = True
            if bot_username and bot_username != bot_settings.bot_username:
                bot_settings.bot_username = bot_username
                updated = True
            if bot_name and bot_name != bot_settings.bot_name:
                bot_settings.bot_name = bot_name
                updated = True
            if api_id and str(api_id) != str(bot_settings.default_api_id):
                bot_settings.default_api_id = api_id
                updated = True
            if api_hash and api_hash != bot_settings.default_api_hash:
                bot_settings.default_api_hash = api_hash
                updated = True
            
            if updated:
                bot_settings.save()
                logger.info("Налаштування бота оновлено успішно")
            else:
                logger.info("Налаштування бота не потребують оновлення")
                
        return bot_settings
    except Exception as e:
        logger.error(f"Помилка при налаштуванні бота: {e}")
        return None

def create_demo_data():
    """Створює демонстраційні дані для тестування"""
    logger.info("Створення демонстраційних даних...")
    
    try:
        # Створюємо демо сесію, якщо немає жодної
        if not TelegramSession.objects.exists():
            logger.info("Створення демонстраційної сесії...")
            session = TelegramSession(
                phone="+380999999999",
                session_name="DemoSession",
                is_active=True,
                is_bot=False,
                needs_auth=True,
                api_id=os.environ.get('API_ID', '19840544'),
                api_hash=os.environ.get('API_HASH', 'c839f28bad345082329ec086fca021fa')
            )
            session.save()
            logger.info(f"Демонстраційна сесія створена: {session}")
        else:
            session = TelegramSession.objects.filter(is_active=True).first()
            logger.info(f"Використовуємо існуючу сесію: {session}")
            
        # Створюємо демо категорію, якщо немає жодної
        if not Category.objects.exists():
            logger.info("Створення демонстраційної категорії...")
            category = Category(
                name="Демо категорія",
                description="Категорія для демонстрації роботи парсера",
                is_active=True,
                session=session
            )
            category.save()
            logger.info(f"Демонстраційна категорія створена: {category}")
        else:
            category = Category.objects.filter(is_active=True).first()
            logger.info(f"Використовуємо існуючу категорію: {category}")
            
        # Створюємо демо канал, якщо немає жодного
        if not Channel.objects.exists():
            logger.info("Створення демонстраційного каналу...")
            channel = Channel(
                name="Демо канал",
                url="https://t.me/channel_hunt_test",
                category=category,
                is_active=True,
                session=session
            )
            channel.save()
            logger.info(f"Демонстраційний канал створено: {channel}")
        else:
            logger.info(f"Демонстраційні канали вже існують: {Channel.objects.count()} шт.")
            
        return True
    except Exception as e:
        logger.error(f"Помилка при створенні демонстраційних даних: {e}")
        return False

def create_superuser(username, email, password):
    """Створює superuser, якщо він не існує"""
    logger.info(f"Перевірка наявності суперкористувача {username}...")
    
    try:
        if not User.objects.filter(username=username).exists():
            logger.info(f"Створення суперкористувача {username}...")
            User.objects.create_superuser(username=username, email=email, password=password)
            logger.info(f"Суперкористувач {username} створено успішно")
            return True
        else:
            logger.info(f"Суперкористувач {username} вже існує")
            return False
    except Exception as e:
        logger.error(f"Помилка при створенні суперкористувача: {e}")
        return False

def main():
    """Головна функція скрипта"""
    parser = argparse.ArgumentParser(description='Швидке налаштування бота Telegram та наповнення бази даних')
    parser.add_argument('--token', help='Токен Telegram бота', default=os.environ.get('BOT_TOKEN', ''))
    parser.add_argument('--api-id', help='API ID Telegram', default=os.environ.get('API_ID', '19840544'))
    parser.add_argument('--api-hash', help='API Hash Telegram', default=os.environ.get('API_HASH', 'c839f28bad345082329ec086fca021fa'))
    parser.add_argument('--username', help="Ім'я користувача для суперкористувача", default='admin')
    parser.add_argument('--email', help='Email для суперкористувача', default='admin@example.com')
    parser.add_argument('--password', help='Пароль для суперкористувача', default='admin')
    parser.add_argument('--no-demo', help='Не створювати демонстраційні дані', action='store_true')
    args = parser.parse_args()
    
    logger.info("=== Запуск налаштування бота ===")
    
    # Налаштовуємо бота
    bot_settings = setup_bot_settings(
        bot_token=args.token,
        api_id=args.api_id,
        api_hash=args.api_hash
    )
    
    # Створюємо суперкористувача
    create_superuser(args.username, args.email, args.password)
    
    # Створюємо демонстраційні дані, якщо потрібно
    if not args.no_demo:
        create_demo_data()
        
    logger.info("=== Налаштування завершено ===")

if __name__ == "__main__":
    main() 