#!/usr/bin/env python3
"""
Скрипт для додавання налаштувань бота через SQL напряму,
оскільки у нас є проблеми з міграціями
"""
import os
import sqlite3
import logging
import sys
from datetime import datetime

# Налаштування логування
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger('direct_db_fix')

def get_db_path():
    """Отримуємо шлях до бази даних (SQLite)"""
    # З змінної середовища
    db_path = os.environ.get('DATABASE_PATH')
    if db_path and os.path.exists(db_path):
        return db_path
        
    # Стандартний шлях
    default_path = 'db.sqlite3'
    if os.path.exists(default_path):
        return default_path
        
    # Шукаємо .sqlite файли в поточній директорії
    for file in os.listdir('.'):
        if file.endswith('.sqlite3'):
            return file
            
    logger.error("Не знайдено файл бази даних SQLite")
    return None

def create_bot_settings_table(conn):
    """Створюємо таблицю admin_panel_botsettings якщо вона не існує"""
    cursor = conn.cursor()
    
    try:
        # Перевіряємо, чи існує таблиця
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='admin_panel_botsettings'")
        if cursor.fetchone():
            logger.info("Таблиця admin_panel_botsettings вже існує")
            return True
            
        # Створюємо таблицю
        logger.info("Створюємо таблицю admin_panel_botsettings")
        cursor.execute('''
        CREATE TABLE admin_panel_botsettings (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            bot_username VARCHAR(100) NOT NULL,
            bot_name VARCHAR(100) NOT NULL,
            bot_token VARCHAR(255),
            default_api_id INTEGER NOT NULL,
            default_api_hash VARCHAR(255),
            polling_interval INTEGER NOT NULL,
            max_messages_per_channel INTEGER NOT NULL,
            auth_guide_text TEXT NOT NULL,
            welcome_message TEXT NOT NULL,
            menu_style VARCHAR(20) NOT NULL,
            created_at DATETIME NOT NULL,
            updated_at DATETIME NOT NULL
        )
        ''')
        conn.commit()
        logger.info("Таблицю admin_panel_botsettings створено успішно")
        return True
    except Exception as e:
        logger.error(f"Помилка при створенні таблиці: {e}")
        conn.rollback()
        return False

def insert_bot_settings(conn, bot_token=None):
    """Додаємо налаштування бота в таблицю"""
    cursor = conn.cursor()
    
    try:
        # Перевіряємо, чи вже є запис в таблиці
        cursor.execute("SELECT COUNT(*) FROM admin_panel_botsettings")
        count = cursor.fetchone()[0]
        
        if count > 0:
            logger.info(f"Вже є {count} записів в таблиці admin_panel_botsettings")
            
            # Якщо переданий токен, оновлюємо його
            if bot_token:
                logger.info(f"Оновлюємо токен бота")
                cursor.execute("UPDATE admin_panel_botsettings SET bot_token = ?, updated_at = ? WHERE id = 1", 
                              (bot_token, datetime.now().strftime('%Y-%m-%d %H:%M:%S')))
                conn.commit()
                logger.info(f"Токен бота оновлено успішно")
            return True
            
        # Додаємо налаштування
        now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        
        cursor.execute('''
        INSERT INTO admin_panel_botsettings (
            bot_username, bot_name, bot_token, default_api_id, default_api_hash,
            polling_interval, max_messages_per_channel, auth_guide_text, welcome_message,
            menu_style, created_at, updated_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            "Channels_hunt_bot",  # bot_username
            "Telegram Channel Parser",  # bot_name
            bot_token or "7923260865:AAGWm7t0Zz2PqFPI5PldEVwrOC4HZ_5oP0c",  # bot_token
            19840544,  # default_api_id
            "c839f28bad345082329ec086fca021fa",  # default_api_hash
            30,  # polling_interval
            10,  # max_messages_per_channel
            "Please follow these steps to authorize your Telegram account",  # auth_guide_text
            "Welcome to the Channel Parser Bot. Use the menu below:",  # welcome_message
            "default",  # menu_style
            now,  # created_at
            now   # updated_at
        ))
        
        conn.commit()
        logger.info("Налаштування бота додано успішно")
        return True
    except Exception as e:
        logger.error(f"Помилка при додаванні налаштувань бота: {e}")
        conn.rollback()
        return False

def main():
    """Головна функція скрипту"""
    # Парсимо аргументи
    bot_token = None
    if len(sys.argv) > 1:
        bot_token = sys.argv[1]
    
    # Отримуємо шлях до бази даних
    db_path = get_db_path()
    if not db_path:
        return False
        
    logger.info(f"Використовуємо базу даних: {db_path}")
    
    try:
        # Підключаємося до бази даних
        conn = sqlite3.connect(db_path)
        
        # Створюємо таблицю якщо потрібно
        if not create_bot_settings_table(conn):
            return False
            
        # Додаємо налаштування
        if not insert_bot_settings(conn, bot_token):
            return False
            
        logger.info("Все готово!")
        return True
    except Exception as e:
        logger.error(f"Непередбачена помилка: {e}")
        return False
    finally:
        if 'conn' in locals():
            conn.close()

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1) 