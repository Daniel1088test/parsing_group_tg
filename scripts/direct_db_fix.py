#!/usr/bin/env python3
"""
Direct database fix script that uses DATABASE_URL connection string
without relying on Django settings.
"""

import os
import sys
import logging
import urllib.parse

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(levelname)s %(asctime)s %(name)s %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S',
)
logger = logging.getLogger('direct_db_fix')

def fix_database_directly():
    """Add missing columns directly to the database if they don't exist"""
    logger.info("Starting direct database fix")
    
    # Get database connection from environment
    db_url = os.environ.get('DATABASE_URL')
    if not db_url:
        logger.error("No DATABASE_URL found, cannot perform direct fixes")
        return False
    
    logger.info("Using DATABASE_URL for connection")
    
    # Parse DATABASE_URL to get connection details
    try:
        parts = urllib.parse.urlparse(db_url)
        
        # Connect to database
        if parts.scheme == 'postgres' or parts.scheme == 'postgresql':
            import psycopg2
            logger.info("Connecting to PostgreSQL database")
            conn = psycopg2.connect(
                dbname=parts.path.lstrip('/'),
                user=parts.username,
                password=parts.password,
                host=parts.hostname,
                port=parts.port or 5432
            )
            return fix_postgres_columns(conn)
        elif parts.scheme == 'sqlite':
            import sqlite3
            logger.info("Connecting to SQLite database")
            db_path = parts.path
            conn = sqlite3.connect(db_path)
            return fix_sqlite_columns(conn)
        else:
            logger.error(f"Unsupported database type: {parts.scheme}")
            return False
            
    except Exception as e:
        logger.error(f"Error parsing or connecting to database: {e}")
        return False

def fix_postgres_columns(conn):
    """Fix PostgreSQL database columns"""
    logger.info("Checking PostgreSQL columns")
    
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
        
        # Check which columns already exist
        cursor.execute(f"""
            SELECT column_name FROM information_schema.columns 
            WHERE table_name = '{table_name}';
        """)
        existing_columns = [row[0] for row in cursor.fetchall()]
        logger.info(f"Existing columns in {table_name}: {existing_columns}")
        
        # Add only missing columns
        for column, data_type in required_columns.items():
            if column not in existing_columns:
                logger.info(f"Adding column '{column}' to {table_name}")
                try:
                    cursor.execute(f"""
                        ALTER TABLE {table_name}
                        ADD COLUMN {column} {data_type};
                    """)
                    logger.info(f"Column '{column}' added successfully")
                except Exception as e:
                    logger.error(f"Error adding column '{column}': {e}")
            else:
                logger.info(f"Column '{column}' already exists, skipping")
        
        cursor.close()
        conn.close()
        logger.info("PostgreSQL column fix completed")
        return True
    except Exception as e:
        logger.error(f"Error fixing PostgreSQL columns: {e}")
        return False

def fix_sqlite_columns(conn):
    """Fix SQLite database columns"""
    logger.info("Checking SQLite columns")
    
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
        
        # Check which columns already exist
        cursor.execute(f"PRAGMA table_info({table_name})")
        existing_columns = [row[1] for row in cursor.fetchall()]
        logger.info(f"Existing columns in {table_name}: {existing_columns}")
        
        # Add only missing columns
        for column, data_type in required_columns.items():
            if column not in existing_columns:
                logger.info(f"Adding column '{column}' to {table_name}")
                try:
                    cursor.execute(f"""
                        ALTER TABLE {table_name}
                        ADD COLUMN {column} {data_type}
                    """)
                    logger.info(f"Column '{column}' added successfully")
                except Exception as e:
                    logger.error(f"Error adding column '{column}': {e}")
            else:
                logger.info(f"Column '{column}' already exists, skipping")
        
        conn.commit()
        cursor.close()
        conn.close()
        logger.info("SQLite column fix completed")
        return True
    except Exception as e:
        logger.error(f"Error fixing SQLite columns: {e}")
        return False

if __name__ == "__main__":
    logger.info("Starting direct database fix script")
    success = fix_database_directly()
    if success:
        logger.info("Database fix completed successfully")
        sys.exit(0)
    else:
        logger.error("Database fix failed")
        sys.exit(1) 