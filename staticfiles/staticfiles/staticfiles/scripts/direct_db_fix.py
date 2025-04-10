#!/usr/bin/env python3
"""
Скрипт для прямого виправлення структури бази даних
без залежності від Django settings та міграцій.
"""

import os
import sys
import logging
import urllib.parse
import importlib.util

# Налаштування логування
logging.basicConfig(
    level=logging.INFO,
    format='%(levelname)s %(asctime)s %(name)s %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S',
)
logger = logging.getLogger('direct_db_fix')

def add_to_path():
    """Додаємо поточну директорію до PYTHONPATH"""
    current_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    if current_dir not in sys.path:
        sys.path.append(current_dir)
        logger.info(f"Додано {current_dir} до PYTHONPATH")

def fix_database_directly():
    """Додаємо відсутні колонки напряму до бази даних"""
    logger.info("Початок прямого виправлення бази даних")
    
    # Отримання рядка підключення до бази даних
    db_url = os.environ.get('DATABASE_URL')
    if not db_url:
        logger.error("Змінна DATABASE_URL не знайдена, неможливо виправити базу даних")
        return False
    
    logger.info("Використовуємо DATABASE_URL для підключення")
    
    # Парсинг DATABASE_URL для отримання деталей підключення
    try:
        parts = urllib.parse.urlparse(db_url)
        
        # Підключення до бази даних
        if parts.scheme == 'postgres' or parts.scheme == 'postgresql':
            # Перевіряємо чи встановлено psycopg2
            if importlib.util.find_spec("psycopg2") is None:
                logger.error("Бібліотека psycopg2 не встановлена")
                return False
                
            import psycopg2
            logger.info("Підключення до PostgreSQL бази даних")
            try:
                conn = psycopg2.connect(
                    dbname=parts.path.lstrip('/'),
                    user=parts.username,
                    password=parts.password,
                    host=parts.hostname,
                    port=parts.port or 5432
                )
                result = fix_postgres_columns(conn)
                conn.close()
                return result
            except psycopg2.Error as e:
                logger.error(f"Помилка підключення до PostgreSQL: {e}")
                return False
        elif parts.scheme == 'sqlite':
            import sqlite3
            logger.info("Підключення до SQLite бази даних")
            db_path = parts.path
            try:
                conn = sqlite3.connect(db_path)
                result = fix_sqlite_columns(conn)
                conn.close()
                return result
            except sqlite3.Error as e:
                logger.error(f"Помилка підключення до SQLite: {e}")
                return False
        else:
            logger.error(f"Непідтримуваний тип бази даних: {parts.scheme}")
            return False
            
    except Exception as e:
        logger.error(f"Помилка парсингу або підключення до бази даних: {e}")
        return False

def fix_postgres_columns(conn):
    """Виправлення колонок у PostgreSQL базі даних"""
    logger.info("Перевірка колонок PostgreSQL")
    
    # Список необхідних колонок та їх типів
    required_columns = {
        'verification_code': 'varchar(10) NULL',
        'password': 'varchar(50) NULL',
        'session_data': 'text NULL',
        'auth_token': 'varchar(255) NULL',
        'needs_auth': 'boolean DEFAULT TRUE',
    }
    
    table_name = 'admin_panel_telegramsession'
    
    try:
        conn.autocommit = True
        cursor = conn.cursor()
        
        # Перевірка існування таблиці
        cursor.execute("""
            SELECT EXISTS (
                SELECT FROM information_schema.tables 
                WHERE table_name = %s
            );
        """, (table_name,))
        
        if not cursor.fetchone()[0]:
            logger.warning(f"Таблиця {table_name} не існує")
            return False
        
        # Перевірка які колонки вже існують
        cursor.execute("""
            SELECT column_name FROM information_schema.columns 
            WHERE table_name = %s;
        """, (table_name,))
        
        existing_columns = [row[0] for row in cursor.fetchall()]
        logger.info(f"Існуючі колонки в {table_name}: {existing_columns}")
        
        # Додаємо тільки відсутні колонки
        for column, data_type in required_columns.items():
            if column.lower() not in [col.lower() for col in existing_columns]:
                logger.info(f"Додаємо колонку '{column}' до {table_name}")
                try:
                    # Використовуємо IF NOT EXISTS для уникнення помилок
                    cursor.execute(f"""
                        ALTER TABLE {table_name}
                        ADD COLUMN IF NOT EXISTS {column} {data_type};
                    """)
                    logger.info(f"Колонка '{column}' успішно додана")
                except Exception as e:
                    logger.error(f"Помилка додавання колонки '{column}': {e}")
            else:
                logger.info(f"Колонка '{column}' вже існує, пропускаємо")
        
        cursor.close()
        logger.info("Виправлення колонок PostgreSQL завершено")
        return True
    except Exception as e:
        logger.error(f"Помилка виправлення колонок PostgreSQL: {e}")
        return False

def fix_sqlite_columns(conn):
    """Виправлення колонок у SQLite базі даних"""
    logger.info("Перевірка колонок SQLite")
    
    # Список необхідних колонок та їх типів
    required_columns = {
        'verification_code': 'TEXT NULL',
        'password': 'TEXT NULL',
        'session_data': 'TEXT NULL',
        'auth_token': 'TEXT NULL',
        'needs_auth': 'INTEGER DEFAULT 1',
    }
    
    table_name = 'admin_panel_telegramsession'
    
    try:
        cursor = conn.cursor()
        
        # Перевірка існування таблиці
        cursor.execute(f"SELECT name FROM sqlite_master WHERE type='table' AND name='{table_name}'")
        if not cursor.fetchone():
            logger.warning(f"Таблиця {table_name} не існує")
            return False
        
        # Перевірка які колонки вже існують
        cursor.execute(f"PRAGMA table_info({table_name})")
        existing_columns = [row[1].lower() for row in cursor.fetchall()]
        logger.info(f"Існуючі колонки в {table_name}: {existing_columns}")
        
        # Додаємо тільки відсутні колонки
        for column, data_type in required_columns.items():
            if column.lower() not in existing_columns:
                logger.info(f"Додаємо колонку '{column}' до {table_name}")
                try:
                    cursor.execute(f"""
                        ALTER TABLE {table_name}
                        ADD COLUMN {column} {data_type}
                    """)
                    logger.info(f"Колонка '{column}' успішно додана")
                except Exception as e:
                    logger.error(f"Помилка додавання колонки '{column}': {e}")
            else:
                logger.info(f"Колонка '{column}' вже існує, пропускаємо")
        
        conn.commit()
        cursor.close()
        logger.info("Виправлення колонок SQLite завершено")
        return True
    except Exception as e:
        logger.error(f"Помилка виправлення колонок SQLite: {e}")
        return False

if __name__ == "__main__":
    logger.info("Запуск скрипту прямого виправлення бази даних")
    # Додаємо поточну директорію до PYTHONPATH
    add_to_path()
    success = fix_database_directly()
    if success:
        logger.info("Виправлення бази даних завершено успішно")
        sys.exit(0)
    else:
        logger.error("Виправлення бази даних завершилось з помилкою")
        sys.exit(1) 