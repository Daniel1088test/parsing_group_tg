#!/usr/bin/env python3
"""
This is a failsafe script that directly adds missing columns to the database tables
using SQL commands. This avoids any migration system complexities when we just need
to ensure certain fields exist in the database schema.
"""

import os
import sys
import logging
import django
from django.db import connection

# Set up Django environment
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "core.settings")
django.setup()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(levelname)s %(asctime)s %(name)s %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S',
)
logger = logging.getLogger('failsafe_db_fix')

def fix_telegramsession_table():
    """Directly add missing columns to the TelegramSession table"""
    logger.info("Starting direct database fix for TelegramSession table")
    
    required_columns = {
        'verification_code': 'varchar(10) NULL',
        'password': 'varchar(50) NULL',
        'session_data': 'text NULL',
        'auth_token': 'varchar(255) NULL',
        'needs_auth': 'boolean DEFAULT TRUE',
    }
    
    cursor = connection.cursor()
    table_name = 'admin_panel_telegramsession'
    
    try:
        # Get existing columns based on database type
        existing_columns = []
        
        if connection.vendor == 'sqlite':
            cursor.execute(f"PRAGMA table_info({table_name})")
            existing_columns = [info[1] for info in cursor.fetchall()]
            logger.info(f"Existing columns in SQLite: {existing_columns}")
            
            # Add missing columns
            for column, data_type in required_columns.items():
                if column not in existing_columns:
                    logger.info(f"Adding column '{column}' to SQLite table")
                    try:
                        # For SQLite, we don't need to handle column exists error, it will fail silently
                        cursor.execute(f"ALTER TABLE {table_name} ADD COLUMN {column} {data_type}")
                        logger.info(f"Successfully added column '{column}'")
                    except Exception as e:
                        logger.error(f"Error adding column '{column}': {e}")
        
        elif connection.vendor == 'postgresql':
            cursor.execute(f"""
                SELECT column_name FROM information_schema.columns 
                WHERE table_name = '{table_name}'
            """)
            existing_columns = [row[0] for row in cursor.fetchall()]
            logger.info(f"Existing columns in PostgreSQL: {existing_columns}")
            
            # Add missing columns
            for column, data_type in required_columns.items():
                if column not in existing_columns:
                    logger.info(f"Adding column '{column}' to PostgreSQL table")
                    try:
                        cursor.execute(f"""
                            ALTER TABLE {table_name} 
                            ADD COLUMN IF NOT EXISTS {column} {data_type}
                        """)
                        logger.info(f"Successfully added column '{column}'")
                    except Exception as e:
                        logger.error(f"Error adding column '{column}': {e}")
        
        logger.info("Finished fixing TelegramSession table")
        return True
    
    except Exception as e:
        logger.error(f"Error fixing database: {e}")
        return False

if __name__ == "__main__":
    logger.info("Starting failsafe database fix script")
    
    success = fix_telegramsession_table()
    
    if success:
        logger.info("Database fix completed successfully")
        sys.exit(0)
    else:
        logger.error("Database fix failed")
        sys.exit(1) 