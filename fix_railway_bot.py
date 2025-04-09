#!/usr/bin/env python3
"""
Скрипт для оновлення налаштувань бота на сервері Railway
та очищення небажаної реклами
"""
import os
import sys
import logging
import json

# Налаштування логування
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Налаштування бота
BOT_TOKEN = "8102516142:AAFTsVXXujHHKoX2KZGqZXBHPBznfgh7kg0"
BOT_USERNAME = "channel_pars_mode_bot"

# Перевірка на середовище Railway
def is_railway():
    """Перевіряє чи виконується скрипт на Railway"""
    return os.environ.get('RAILWAY_ENVIRONMENT') is not None

def update_env_variables():
    """Оновлює змінні середовища для Railway"""
    os.environ['BOT_TOKEN'] = BOT_TOKEN
    os.environ['BOT_USERNAME'] = BOT_USERNAME
    logger.info("✓ Змінні середовища оновлено")

def update_config_files():
    """Оновлює всі конфігураційні файли"""
    logger.info("Оновлення конфігураційних файлів...")
    
    # 1. Оновлюємо .env
    if os.path.exists('.env'):
        try:
            with open('.env', 'r', encoding='utf-8') as f:
                lines = f.readlines()
            
            with open('.env', 'w', encoding='utf-8') as f:
                token_updated = False
                username_updated = False
                
                for line in lines:
                    if line.startswith('BOT_TOKEN='):
                        f.write(f"BOT_TOKEN={BOT_TOKEN}\n")
                        token_updated = True
                    elif line.startswith('BOT_USERNAME='):
                        f.write(f"BOT_USERNAME={BOT_USERNAME}\n")
                        username_updated = True
                    else:
                        f.write(line)
                
                # Додаємо змінні, якщо вони не існують
                if not token_updated:
                    f.write(f"\nBOT_TOKEN={BOT_TOKEN}\n")
                if not username_updated:
                    f.write(f"BOT_USERNAME={BOT_USERNAME}\n")
            
            logger.info("✓ Файл .env оновлено")
        except Exception as e:
            logger.error(f"Помилка оновлення .env: {e}")
    
    # 2. Оновлюємо config.py
    config_path = os.path.join('tg_bot', 'config.py')
    if os.path.exists(config_path):
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Оновлюємо токен і ім'я
            import re
            content = re.sub(
                r'(TOKEN_BOT\s*=\s*os\.environ\.get\([\'"]BOT_TOKEN[\'"]\s*,\s*)[\'"].*?[\'"]',
                f'\\1"{BOT_TOKEN}"',
                content
            )
            content = re.sub(
                r'(BOT_USERNAME\s*=\s*os\.environ\.get\([\'"]BOT_USERNAME[\'"]\s*,\s*)[\'"].*?[\'"]',
                f'\\1"{BOT_USERNAME}"',
                content
            )
            
            with open(config_path, 'w', encoding='utf-8') as f:
                f.write(content)
            
            logger.info(f"✓ Файл {config_path} оновлено")
        except Exception as e:
            logger.error(f"Помилка оновлення {config_path}: {e}")
    
    # 3. Оновлюємо bot_token.env
    try:
        with open('bot_token.env', 'w', encoding='utf-8') as f:
            f.write(f"BOT_TOKEN={BOT_TOKEN}")
        logger.info("✓ Файл bot_token.env оновлено")
    except Exception as e:
        logger.error(f"Помилка оновлення bot_token.env: {e}")
    
    # 4. Оновлюємо direct_bot_runner.py
    bot_runner_path = 'direct_bot_runner.py'
    if os.path.exists(bot_runner_path):
        try:
            with open(bot_runner_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Оновлюємо токен
            import re
            content = re.sub(
                r"os\.environ\['BOT_TOKEN'\]\s*=\s*['\"].*?['\"]",
                f"os.environ['BOT_TOKEN'] = \"{BOT_TOKEN}\"",
                content
            )
            content = re.sub(
                r"token\s*=\s*['\"].*?['\"]",
                f"token = \"{BOT_TOKEN}\"",
                content
            )
            
            with open(bot_runner_path, 'w', encoding='utf-8') as f:
                f.write(content)
            
            logger.info(f"✓ Файл {bot_runner_path} оновлено")
        except Exception as e:
            logger.error(f"Помилка оновлення {bot_runner_path}: {e}")

def update_database():
    """Оновлює налаштування бота в базі даних"""
    logger.info("Оновлення налаштувань бота в базі даних...")
    
    try:
        # Ініціалізуємо Django
        os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
        import django
        django.setup()
        
        # Імпортуємо моделі
        from django.db import transaction
        from admin_panel.models import BotSettings, Message, Channel
        
        # Оновлюємо або створюємо налаштування бота
        with transaction.atomic():
            bot_settings = BotSettings.objects.first()
            if bot_settings:
                bot_settings.bot_token = BOT_TOKEN
                bot_settings.bot_username = BOT_USERNAME
                bot_settings.save()
                logger.info("✓ Налаштування бота оновлено")
            else:
                BotSettings.objects.create(
                    bot_token=BOT_TOKEN,
                    bot_username=BOT_USERNAME,
                    bot_name="Channel Parsing Bot"
                )
                logger.info("✓ Створено нові налаштування бота")
        
        # Видаляємо рекламу VPN
        try:
            # Ключові слова для видалення повідомлень з рекламою
            vpn_keywords = [
                "speeeeedvpnbot",
                "@speeeeedvpnbot",
                "vpn прямо в telegram",
                "быстрый, и стабильный",
                "поддерживаются все устройства",
                "начать пробный период",
                "7 дней абсолютно бесплатно",
                "откройте vpn",
                "youtube instagram",
                "и другие - летают",
                "ios/android/windows/mac",
                "роутеры, и тд"
            ]
            
            # Видаляємо повідомлення з рекламою VPN
            from django.db.models import Q
            query = Q()
            for keyword in vpn_keywords:
                query |= Q(text__icontains=keyword)
            
            vpn_messages = Message.objects.filter(query)
            count = vpn_messages.count()
            if count > 0:
                vpn_messages.delete()
                logger.info(f"✓ Видалено {count} повідомлень з рекламою VPN")
            else:
                logger.info("Повідомлень з рекламою VPN не знайдено")
            
            # Деактивуємо канали з VPN
            vpn_channels = Channel.objects.filter(
                Q(name__icontains="vpn") | Q(url__icontains="vpn") | Q(url__icontains="speeeeedvpnbot")
            )
            
            if vpn_channels.exists():
                for channel in vpn_channels:
                    channel.is_active = False
                    channel.save()
                logger.info(f"✓ Деактивовано {vpn_channels.count()} каналів з VPN")
        except Exception as e:
            logger.error(f"Помилка при очищенні реклами: {e}")
    except Exception as e:
        logger.error(f"Помилка при роботі з базою даних: {e}")

def main():
    """Основна функція оновлення налаштувань"""
    logger.info("=== Початок оновлення налаштувань бота ===")
    
    # Оновлюємо змінні середовища
    update_env_variables()
    
    # Оновлюємо конфігураційні файли
    update_config_files()
    
    # Оновлюємо базу даних
    update_database()
    
    logger.info("=== Оновлення налаштувань бота завершено ===")
    logger.info("=== Щоб застосувати зміни, перезапустіть бота ===")

if __name__ == "__main__":
    # Перевіряємо якщо ми на Railway
    if is_railway():
        logger.info("Скрипт виконується на сервері Railway")
    else:
        logger.info("Скрипт виконується локально")
    
    # Виконуємо оновлення налаштувань
    main()
    
    sys.exit(0) 