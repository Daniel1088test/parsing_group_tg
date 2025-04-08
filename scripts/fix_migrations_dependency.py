#!/usr/bin/env python
"""
Script to fix Django migration dependencies and ensure database compatibility
"""
import os
import sys
import django
import logging
from importlib import import_module
from django.db import connection, ProgrammingError

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S',
)
logger = logging.getLogger('fix_migrations')

# Initialize Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()

def get_applied_migrations():
    """Get a list of applied migrations from the database"""
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT app, name FROM django_migrations")
            return {f"{row[0]}.{row[1]}" for row in cursor.fetchall()}
    except ProgrammingError:
        logger.error("django_migrations table doesn't exist yet")
        return set()
    except Exception as e:
        logger.error(f"Error getting migrations: {e}")
        return set()

def ensure_column_exists(table_name, column_name, column_type, default=None):
    """Ensure a column exists in a table by adding it if it doesn't"""
    try:
        with connection.cursor() as cursor:
            # Check if the column exists
            cursor.execute(f"""
                SELECT column_name 
                FROM information_schema.columns 
                WHERE table_name = '{table_name}' AND column_name = '{column_name}'
            """)
            
            if cursor.fetchone() is None:
                # Column doesn't exist, add it
                if default is not None:
                    sql = f"ALTER TABLE {table_name} ADD COLUMN {column_name} {column_type} DEFAULT {default}"
                else:
                    sql = f"ALTER TABLE {table_name} ADD COLUMN {column_name} {column_type}"
                
                cursor.execute(sql)
                logger.info(f"Added column '{column_name}' to table '{table_name}'")
                connection.commit()
                return True
            else:
                logger.info(f"Column '{column_name}' already exists in table '{table_name}'")
                return True
    except Exception as e:
        logger.error(f"Error ensuring column '{column_name}' exists: {e}")
        connection.rollback()
        return False

def fix_migrations():
    """Apply migrations-related fixes"""
    logger.info("Checking migrations and database compatibility...")
    
    # Get applied migrations
    applied = get_applied_migrations()
    logger.info(f"Found {len(applied)} applied migrations")
    
    # Ensure critical columns exist in TelegramSession
    telegram_session_columns = [
        ('verification_code', 'VARCHAR(255)', 'NULL'),
        ('password', 'VARCHAR(255)', 'NULL'),
        ('session_data', 'TEXT', 'NULL'),
        ('auth_token', 'VARCHAR(255)', 'NULL'),
        ('needs_auth', 'BOOLEAN', 'FALSE')
    ]
    
    for column_name, column_type, default in telegram_session_columns:
        ensure_column_exists('admin_panel_telegramsession', column_name, column_type, default)
    
    logger.info("Migration and database compatibility check completed")
    return True

if __name__ == "__main__":
    try:
        success = fix_migrations()
        sys.exit(0 if success else 1)
    except Exception as e:
        logger.error(f"Unhandled error: {e}")
        sys.exit(1) 