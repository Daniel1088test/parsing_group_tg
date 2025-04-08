#!/usr/bin/env python
"""
Direct database fix script that works even when Django ORM is not available.
This script directly connects to the PostgreSQL database and adds missing columns.
"""
import os
import sys
import logging
import time
import traceback
from urllib.parse import urlparse
from pathlib import Path

# Add the parent directory to the Python path
sys.path.insert(0, str(Path(__file__).resolve().parent))

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s %(name)s %(levelname)s %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S',
)
logger = logging.getLogger('direct_db_fix')

def get_db_connection():
    """Get database connection from DATABASE_URL environment variable"""
    try:
        # Try to get DATABASE_URL from environment
        database_url = os.environ.get('DATABASE_URL')
        
        if not database_url:
            logger.error("DATABASE_URL environment variable not set!")
            
            # Railway specific: try with alternate env var names
            for env_var in ['PGDATABASE', 'DATABASE_PRIVATE_URL', 'DATABASE_PUBLIC_URL']:
                if os.environ.get(env_var):
                    logger.info(f"Using {env_var} for database connection")
                    database_url = os.environ.get(env_var)
                    break
                    
            if not database_url:
                logger.warning("No database URL found, using SQLite as fallback")
                import sqlite3
                conn = sqlite3.connect('db.sqlite3')
                return conn, 'sqlite'
        
        logger.info("Using DATABASE_URL for database connection")
        
        # Import psycopg2 here to avoid import errors if not installed
        try:
            import psycopg2
        except ImportError:
            logger.error("psycopg2 not installed, trying to install it now...")
            import subprocess
            subprocess.check_call([sys.executable, "-m", "pip", "install", "psycopg2-binary"])
            import psycopg2
        
        # Parse the database URL
        result = urlparse(database_url)
        
        # Extract the components
        database = result.path[1:]
        username = result.username
        password = result.password
        hostname = result.hostname
        port = result.port
        
        # Create connection with retry logic
        max_retries = 5
        retry_delay = 1
        last_error = None
        
        for attempt in range(max_retries):
            try:
                connection = psycopg2.connect(
                    database=database,
                    user=username,
                    password=password,
                    host=hostname,
                    port=port
                )
                
                # Test the connection
                with connection.cursor() as cursor:
                    cursor.execute("SELECT version();")
                    db_version = cursor.fetchone()
                    logger.info(f"Connected to PostgreSQL: {db_version[0][:30]}...")
                
                return connection, 'postgres'
            except Exception as e:
                last_error = e
                if attempt < max_retries - 1:
                    logger.warning(f"Connection attempt {attempt+1} failed: {e}. Retrying in {retry_delay}s...")
                    time.sleep(retry_delay)
                    retry_delay *= 2  # Exponential backoff
                else:
                    logger.error(f"Failed to connect after {max_retries} attempts: {e}")
        
        if last_error:
            raise last_error
        
    except Exception as e:
        logger.error(f"Error connecting to database: {e}")
        logger.error(traceback.format_exc())
        return None, None

def check_table_exists(connection, table_name, db_type='postgres'):
    """Check if a table exists in the database"""
    try:
        with connection.cursor() as cursor:
            if db_type == 'postgres':
                cursor.execute(f"""
                    SELECT EXISTS (
                        SELECT FROM information_schema.tables 
                        WHERE table_name = '{table_name}'
                    );
                """)
                return cursor.fetchone()[0]
            elif db_type == 'sqlite':
                cursor.execute(f"""
                    SELECT name FROM sqlite_master 
                    WHERE type='table' AND name='{table_name}';
                """)
                return cursor.fetchone() is not None
        return False
    except Exception as e:
        logger.error(f"Error checking if table exists: {e}")
        return False

def check_column_exists(connection, table_name, column_name, db_type='postgres'):
    """Check if a column exists in a table"""
    try:
        with connection.cursor() as cursor:
            if db_type == 'postgres':
                cursor.execute(f"""
                    SELECT column_name 
                    FROM information_schema.columns 
                    WHERE table_name = '{table_name}' AND column_name = '{column_name}';
                """)
                return cursor.fetchone() is not None
            elif db_type == 'sqlite':
                cursor.execute(f"PRAGMA table_info({table_name});")
                columns = cursor.fetchall()
                column_names = [col[1] for col in columns]
                return column_name in column_names
    except Exception as e:
        logger.error(f"Error checking if column exists: {e}")
        return False

def add_column(connection, table_name, column_name, column_type, default=None, db_type='postgres'):
    """Add a column to a table if it doesn't exist"""
    try:
        # First check if table exists
        if not check_table_exists(connection, table_name, db_type):
            logger.warning(f"Table '{table_name}' does not exist, skipping column addition")
            return False
            
        # First check if column exists
        if check_column_exists(connection, table_name, column_name, db_type):
            logger.info(f"Колонка '{column_name}' вже існує, пропускаємо")
            return True
            
        with connection.cursor() as cursor:
            # Build SQL statement based on whether a default is provided
            if db_type == 'postgres':
                if default is not None:
                    sql = f"ALTER TABLE {table_name} ADD COLUMN {column_name} {column_type} DEFAULT {default};"
                else:
                    sql = f"ALTER TABLE {table_name} ADD COLUMN {column_name} {column_type};"
            elif db_type == 'sqlite':
                # SQLite has limited ALTER TABLE support
                if default is not None:
                    sql = f"ALTER TABLE {table_name} ADD COLUMN {column_name} {column_type} DEFAULT {default};"
                else:
                    sql = f"ALTER TABLE {table_name} ADD COLUMN {column_name} {column_type};"
                
            cursor.execute(sql)
            connection.commit()
            logger.info(f"Колонка '{column_name}' успішно додана")
            return True
    except Exception as e:
        logger.error(f"Помилка додавання колонки '{column_name}': {e}")
        logger.error(traceback.format_exc())
        try:
            connection.rollback()
        except:
            pass
        return False

def fix_database():
    """Apply all necessary database fixes"""
    # Maximum retry attempts
    max_retries = 5
    retry_delay = 2  # seconds
    
    for attempt in range(max_retries):
        try:
            connection, db_type = get_db_connection()
            if not connection:
                logger.error("Could not connect to database, retrying...")
                time.sleep(retry_delay)
                continue
            
            if db_type == 'sqlite':
                logger.info("Using SQLite database, limited column modification support")
                
            # Fix TelegramSession table
            session_table = 'admin_panel_telegramsession'
            
            # First ensure the table exists - if not, migrations need to run first
            if not check_table_exists(connection, session_table, db_type):
                logger.warning(f"Table '{session_table}' does not exist yet. Run migrations first.")
                # Try to create a minimal table structure if we're desperate
                if attempt == max_retries - 1:  # Last attempt, try emergency creation
                    try:
                        logger.info("Attempting emergency table creation...")
                        with connection.cursor() as cursor:
                            if db_type == 'postgres':
                                cursor.execute(f"""
                                    CREATE TABLE IF NOT EXISTS {session_table} (
                                        id SERIAL PRIMARY KEY,
                                        phone VARCHAR(20) UNIQUE NOT NULL,
                                        api_id VARCHAR(10),
                                        api_hash VARCHAR(32),
                                        is_active BOOLEAN DEFAULT TRUE,
                                        session_file VARCHAR(255),
                                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                                        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                                    );
                                """)
                            elif db_type == 'sqlite':
                                cursor.execute(f"""
                                    CREATE TABLE IF NOT EXISTS {session_table} (
                                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                                        phone VARCHAR(20) UNIQUE NOT NULL,
                                        api_id VARCHAR(10),
                                        api_hash VARCHAR(32),
                                        is_active BOOLEAN DEFAULT 1,
                                        session_file VARCHAR(255),
                                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                                        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                                    );
                                """)
                            connection.commit()
                            logger.info(f"Created emergency table structure for {session_table}")
                    except Exception as e:
                        logger.error(f"Emergency table creation failed: {e}")
            
            # Define columns to add
            telegram_session_columns = [
                ('verification_code', 'VARCHAR(255)', 'NULL'),
                ('password', 'VARCHAR(255)', 'NULL'),
                ('session_data', 'TEXT', 'NULL'),
                ('auth_token', 'VARCHAR(255)', 'NULL'),
                ('needs_auth', 'BOOLEAN', 'FALSE')
            ]
            
            # Add each column
            for column_name, column_type, default in telegram_session_columns:
                add_column(connection, session_table, column_name, column_type, default, db_type)
            
            # Fix BotSettings table if needed
            bot_settings_table = 'admin_panel_botsettings'
            if check_table_exists(connection, bot_settings_table, db_type):
                bot_settings_columns = [
                    ('bot_token', 'VARCHAR(255)', 'NULL'),
                    ('default_api_id', 'INTEGER', '2496'),
                    ('default_api_hash', 'VARCHAR(255)', 'NULL'),
                    ('polling_interval', 'INTEGER', '30'),
                    ('max_messages_per_channel', 'INTEGER', '10')
                ]
                
                for column_name, column_type, default in bot_settings_columns:
                    add_column(connection, bot_settings_table, column_name, column_type, default, db_type)
            
            logger.info("Виправлення колонок бази даних завершено")
            
            # Close connection
            connection.close()
            logger.info("Виправлення бази даних завершено успішно")
            return True
        except Exception as e:
            logger.error(f"Помилка виправлення бази даних: {e}")
            logger.error(traceback.format_exc())
            if attempt < max_retries - 1:
                retry_delay *= 2  # Exponential backoff
                logger.info(f"Повторна спроба через {retry_delay} секунд... ({attempt+1}/{max_retries})")
                time.sleep(retry_delay)
            else:
                logger.error(f"Вичерпано максимальну кількість спроб ({max_retries})")
                return False

if __name__ == "__main__":
    # If a command-line argument is provided, use it as DATABASE_URL
    if len(sys.argv) > 1:
        os.environ['DATABASE_URL'] = sys.argv[1]
        
    # Run the database fix
    success = fix_database()
    
    # Exit with appropriate code
    sys.exit(0 if success else 1)