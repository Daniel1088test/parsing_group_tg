#!/usr/bin/env python3
"""
Скрипт для видалення рекламних повідомлень про VPN з бази даних
Спеціальна версія для Railway з мінімальною кількістю залежностей
"""
import os
import sys
import django
import logging

# Налаштування логування
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Ініціалізація Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()

# Імпорт моделей
from django.db import connection, transaction
from admin_panel.models import Message, Channel

def direct_db_cleanup():
    """Видаляє спам через прямі SQL-запити для швидкості"""
    
    # Ключові слова для ідентифікації VPN-реклами
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
    
    # Отримуємо всі повідомлення, які містять рекламу VPN
    with connection.cursor() as cursor:
        # Створюємо тимчасову таблицю для зберігання ID повідомлень зі спамом
        cursor.execute("""
            CREATE TEMP TABLE spam_messages (
                id INTEGER PRIMARY KEY
            );
        """)
        
        # Заповнюємо тимчасову таблицю
        total_found = 0
        for keyword in vpn_keywords:
            try:
                cursor.execute("""
                    INSERT INTO spam_messages (id)
                    SELECT id FROM admin_panel_message 
                    WHERE text ILIKE %s AND id NOT IN (SELECT id FROM spam_messages);
                """, [f'%{keyword}%'])
                
                # Отримуємо кількість вставлених рядків
                cursor.execute("SELECT COUNT(*) FROM spam_messages;")
                current_count = cursor.fetchone()[0]
                
                logger.info(f"Знайдено {current_count - total_found} повідомлень з ключовим словом '{keyword}'")
                total_found = current_count
            except Exception as e:
                logger.error(f"Помилка при пошуку повідомлень з ключовим словом '{keyword}': {e}")
        
        logger.info(f"Всього знайдено {total_found} рекламних повідомлень про VPN")
        
        # Видаляємо всі спам-повідомлення за один раз
        try:
            cursor.execute("""
                DELETE FROM admin_panel_message 
                WHERE id IN (SELECT id FROM spam_messages);
            """)
            logger.info(f"✓ Видалено всі {total_found} спам-повідомлень з бази даних")
        except Exception as e:
            logger.error(f"Помилка при видаленні спам-повідомлень: {e}")

def remove_vpn_channels():
    """Знаходить і деактивує канали, пов'язані з VPN"""
    
    try:
        # Знаходимо канали, які містять "vpn" в URL або назві
        vpn_channels = Channel.objects.filter(
            url__icontains="vpn"
        ) | Channel.objects.filter(
            name__icontains="vpn"
        )
        
        if vpn_channels.exists():
            logger.warning(f"Знайдено {vpn_channels.count()} каналів, пов'язаних з VPN")
            for channel in vpn_channels:
                logger.warning(f"Канал: {channel.name} ({channel.url})")
                # Деактивуємо канал
                channel.is_active = False
                channel.save()
                logger.info(f"✓ Канал '{channel.name}' деактивовано")
        
        # Окремо перевіряємо канали, які містять "speeeeedvpnbot"
        vpn_bot_channels = Channel.objects.filter(
            url__icontains="speeeeedvpnbot"
        )
        
        if vpn_bot_channels.exists():
            logger.error(f"Знайдено {vpn_bot_channels.count()} каналів, пов'язаних з SpeeeeedVPNbot")
            for channel in vpn_bot_channels:
                logger.error(f"Канал: {channel.name} ({channel.url})")
                # Повністю видаляємо канал
                channel.delete()
                logger.info(f"✓ Канал '{channel.name}' видалено")
        
    except Exception as e:
        logger.error(f"Помилка при роботі з каналами: {e}")

def clear_message_cache():
    """Очищає кеш повідомлень"""
    
    cache_dirs = [
        os.path.join(os.getcwd(), 'media', 'messages'),
        os.path.join(os.getcwd(), 'staticfiles', 'cache')
    ]
    
    import shutil
    for cache_dir in cache_dirs:
        if os.path.exists(cache_dir):
            logger.info(f"Очищення кешу: {cache_dir}")
            try:
                # Очищаємо вміст директорії, але не видаляємо саму директорію
                for item in os.listdir(cache_dir):
                    item_path = os.path.join(cache_dir, item)
                    try:
                        if os.path.isfile(item_path):
                            os.unlink(item_path)
                        elif os.path.isdir(item_path):
                            shutil.rmtree(item_path)
                    except Exception as e:
                        logger.error(f"Помилка при видаленні {item_path}: {e}")
            except Exception as e:
                logger.error(f"Помилка при очищенні кешу {cache_dir}: {e}")

if __name__ == "__main__":
    logger.info("Починаємо очищення бази даних від рекламного спаму...")
    
    try:
        # Виконуємо всі операції в транзакції
        with transaction.atomic():
            direct_db_cleanup()
            remove_vpn_channels()
        
        # Очищаємо кеш повідомлень
        clear_message_cache()
        
        logger.info("✅ Очищення успішно завершено!")
        
    except Exception as e:
        logger.error(f"❌ Критична помилка під час виконання: {e}")
        sys.exit(1)
    
    sys.exit(0) 