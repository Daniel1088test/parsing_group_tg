#!/usr/bin/env python3
"""
Script to fix all missing fields in database models
"""
import os
import sys
import logging
import traceback
import django

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger('fix_model_fields')

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')

try:
    django.setup()
    logger.info("Django initialized successfully")
except Exception as e:
    logger.error(f"Error initializing Django: {e}")
    sys.exit(1)

from django.db import connection
from django.db.utils import ProgrammingError, OperationalError, IntegrityError

def fix_telegramsession_fields():
    """Fix all missing fields in TelegramSession model"""
    with connection.cursor() as cursor:
        fields_to_add = [
            {
                "name": "is_authorized",
                "pg_sql": "ALTER TABLE admin_panel_telegramsession ADD COLUMN is_authorized BOOLEAN DEFAULT FALSE",
                "sqlite_sql": "ALTER TABLE admin_panel_telegramsession ADD COLUMN is_authorized BOOLEAN DEFAULT 0"
            },
            {
                "name": "last_activity",
                "pg_sql": "ALTER TABLE admin_panel_telegramsession ADD COLUMN last_activity TIMESTAMP WITH TIME ZONE DEFAULT NOW()",
                "sqlite_sql": "ALTER TABLE admin_panel_telegramsession ADD COLUMN last_activity TIMESTAMP"
            },
            # Add more fields that might be missing
            {
                "name": "needs_auth",
                "pg_sql": "ALTER TABLE admin_panel_telegramsession ADD COLUMN needs_auth BOOLEAN DEFAULT FALSE",
                "sqlite_sql": "ALTER TABLE admin_panel_telegramsession ADD COLUMN needs_auth BOOLEAN DEFAULT 0"
            }
        ]
        
        for field in fields_to_add:
            try:
                # Check if field exists
                try:
                    cursor.execute(f"SELECT {field['name']} FROM admin_panel_telegramsession LIMIT 1")
                    logger.info(f"Field {field['name']} already exists")
                except (ProgrammingError, OperationalError) as e:
                    logger.info(f"Field {field['name']} does not exist: {e}")
                    
                    # Try to add with PostgreSQL syntax
                    try:
                        cursor.execute(field['pg_sql'])
                        logger.info(f"Successfully added {field['name']} field using PostgreSQL syntax")
                    except Exception as pg_e:
                        logger.warning(f"PostgreSQL ALTER failed for {field['name']}: {pg_e}")
                        
                        # Fallback to SQLite syntax
                        try:
                            cursor.execute(field['sqlite_sql'])
                            logger.info(f"Successfully added {field['name']} field using SQLite syntax")
                        except Exception as sqlite_e:
                            logger.error(f"SQLite ALTER failed for {field['name']}: {sqlite_e}")
            except Exception as e:
                logger.error(f"Error processing field {field['name']}: {e}")
    
    logger.info("Finished fixing TelegramSession fields")
    return True

def fix_channel_fields():
    """Fix fields in Channel model"""
    with connection.cursor() as cursor:
        fields_to_add = [
            {
                "name": "is_active",
                "pg_sql": "ALTER TABLE admin_panel_channel ADD COLUMN is_active BOOLEAN DEFAULT TRUE",
                "sqlite_sql": "ALTER TABLE admin_panel_channel ADD COLUMN is_active BOOLEAN DEFAULT 1"
            }
        ]
        
        for field in fields_to_add:
            try:
                # Check if field exists
                try:
                    cursor.execute(f"SELECT {field['name']} FROM admin_panel_channel LIMIT 1")
                    logger.info(f"Field {field['name']} already exists in Channel model")
                except (ProgrammingError, OperationalError) as e:
                    logger.info(f"Field {field['name']} does not exist in Channel model: {e}")
                    
                    # Try to add with PostgreSQL syntax
                    try:
                        cursor.execute(field['pg_sql'])
                        logger.info(f"Successfully added {field['name']} field to Channel model using PostgreSQL syntax")
                    except Exception as pg_e:
                        logger.warning(f"PostgreSQL ALTER failed for Channel.{field['name']}: {pg_e}")
                        
                        # Fallback to SQLite syntax
                        try:
                            cursor.execute(field['sqlite_sql'])
                            logger.info(f"Successfully added {field['name']} field to Channel model using SQLite syntax")
                        except Exception as sqlite_e:
                            logger.error(f"SQLite ALTER failed for Channel.{field['name']}: {sqlite_e}")
            except Exception as e:
                logger.error(f"Error processing Channel field {field['name']}: {e}")
    
    logger.info("Finished fixing Channel fields")
    return True

def fix_broken_relationships():
    """Fix broken relationships between models"""
    with connection.cursor() as cursor:
        try:
            # Fix Channel model session references
            try:
                cursor.execute("""
                    SELECT c.id, c.session_id 
                    FROM admin_panel_channel c
                    LEFT JOIN admin_panel_telegramsession t ON c.session_id = t.id
                    WHERE c.session_id IS NOT NULL AND t.id IS NULL
                """)
                invalid_sessions = cursor.fetchall()
                
                if invalid_sessions:
                    logger.info(f"Found {len(invalid_sessions)} channels with invalid session references")
                    for channel_id, session_id in invalid_sessions:
                        try:
                            cursor.execute(
                                "UPDATE admin_panel_channel SET session_id = NULL WHERE id = %s",
                                [channel_id]
                            )
                            logger.info(f"Fixed channel {channel_id} (invalid session_id {session_id})")
                        except Exception as update_error:
                            logger.error(f"Error updating channel {channel_id}: {update_error}")
                else:
                    logger.info("No channels with invalid session references found")
            except Exception as e:
                logger.error(f"Error checking channel-session relationships: {e}")
            
            # Fix Category model session references
            try:
                cursor.execute("""
                    SELECT c.id, c.session_id 
                    FROM admin_panel_category c
                    LEFT JOIN admin_panel_telegramsession t ON c.session_id = t.id
                    WHERE c.session_id IS NOT NULL AND t.id IS NULL
                """)
                invalid_sessions = cursor.fetchall()
                
                if invalid_sessions:
                    logger.info(f"Found {len(invalid_sessions)} categories with invalid session references")
                    for category_id, session_id in invalid_sessions:
                        try:
                            cursor.execute(
                                "UPDATE admin_panel_category SET session_id = NULL WHERE id = %s",
                                [category_id]
                            )
                            logger.info(f"Fixed category {category_id} (invalid session_id {session_id})")
                        except Exception as update_error:
                            logger.error(f"Error updating category {category_id}: {update_error}")
                else:
                    logger.info("No categories with invalid session references found")
            except Exception as e:
                logger.error(f"Error checking category-session relationships: {e}")
                
        except Exception as e:
            logger.error(f"Error fixing relationships: {e}")
            logger.error(traceback.format_exc())
    
    logger.info("Finished fixing broken relationships")
    return True

def main():
    """Main function"""
    logger.info("Starting model fields fixes...")
    
    # Fix TelegramSession fields
    fix_telegramsession_fields()
    
    # Fix Channel fields
    fix_channel_fields()
    
    # Fix broken relationships
    fix_broken_relationships()
    
    logger.info("All model field fixes completed")
    return True

if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        logger.error(f"Unhandled error: {e}")
        logger.error(traceback.format_exc())
        sys.exit(1) 