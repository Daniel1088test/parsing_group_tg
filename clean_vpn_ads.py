#!/usr/bin/env python3
"""
Скрипт для видалення рекламних повідомлень про VPN з бази даних
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
from admin_panel.models import Message, Channel, TelegramSession

def delete_vpn_spam():
    """Видаляє всі спам-повідомлення про VPN з бази даних"""
    
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
    
    total_deleted = 0
    
    # Видаляємо повідомлення по кожному ключовому слову
    for keyword in vpn_keywords:
        try:
            spam_messages = Message.objects.filter(text__icontains=keyword)
            count = spam_messages.count()
            
            if count > 0:
                logger.info(f"Знайдено {count} повідомлень з ключовим словом '{keyword}'")
                # Запам'ятовуємо ідентифікатори каналів, що надсилають спам
                spam_channels = set()
                for msg in spam_messages:
                    if hasattr(msg, 'channel') and msg.channel:
                        spam_channels.add(msg.channel.id)
                
                # Видаляємо повідомлення
                spam_messages.delete()
                total_deleted += count
                logger.info(f"✓ Видалено {count} повідомлень")
                
                # Виводимо інформацію про канали
                if spam_channels:
                    channels = Channel.objects.filter(id__in=spam_channels)
                    logger.info(f"⚠️ VPN реклама надходила з {len(channels)} каналів:")
                    for channel in channels:
                        logger.info(f"   - {channel.name} ({channel.url})")
            
        except Exception as e:
            logger.error(f"Помилка при видаленні повідомлень з ключовим словом '{keyword}': {e}")
    
    logger.info(f"✅ Всього видалено {total_deleted} рекламних повідомлень про VPN")
    
    # Перевіряємо чи є сесія чи канал для SpeeeeedVPNbot
    check_vpn_channels()

def check_vpn_channels():
    """Перевіряє чи є канали та сесії пов'язані з VPN-ботом"""
    
    # Перевіряємо канали з "vpn" в назві або URL
    vpn_channels = Channel.objects.filter(
        name__icontains="vpn"
    ) | Channel.objects.filter(
        url__icontains="vpn"
    )
    
    if vpn_channels.exists():
        logger.warning(f"⚠️ Виявлено {vpn_channels.count()} каналів, пов'язаних з VPN:")
        for channel in vpn_channels:
            logger.warning(f"   - {channel.name} ({channel.url})")
            logger.warning(f"     Рекомендуємо видалити цей канал або деактивувати його.")
    
    # Перевіряємо, чи в URL каналів є посилання на @speeeeedvpnbot
    vpn_specific = Channel.objects.filter(
        url__icontains="speeeeedvpnbot"
    )
    
    if vpn_specific.exists():
        logger.error(f"❌ УВАГА! Виявлено {vpn_specific.count()} каналів, прямо пов'язаних з SpeeeeedVPNbot:")
        for channel in vpn_specific:
            logger.error(f"   - {channel.name} ({channel.url})")
            # Деактивуємо цей канал
            channel.is_active = False
            channel.save()
            logger.info(f"   ✓ Канал деактивовано")

def fix_message_display():
    """Вирішує проблему відображення повідомлень у боті"""
    
    # Видаляємо кеш повідомлень
    try:
        import shutil
        cache_dirs = [
            os.path.join(os.getcwd(), 'media', 'messages'),
            os.path.join(os.getcwd(), 'staticfiles', 'cache')
        ]
        
        for cache_dir in cache_dirs:
            if os.path.exists(cache_dir):
                logger.info(f"Очищення кешу: {cache_dir}")
                # Не видаляємо директорію, а тільки її вміст
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
        logger.error(f"Помилка при очищенні кешу: {e}")

if __name__ == "__main__":
    logger.info("Починаємо очищення бази даних від спаму...")
    delete_vpn_spam()
    fix_message_display()
    logger.info("Очищення завершено!") 