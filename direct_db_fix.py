import os
import logging
import psycopg2
import time
import sys
from urllib.parse import urlparse

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
        database_url = os.environ.get('DATABASE_URL')
        
        if not database_url:
            logger.error("DATABASE_URL environment variable not set!")
            return None
            
        logger.info("Using DATABASE_URL for database connection")
        
        # Parse the database URL
        result = urlparse(database_url)
        
        # Extract the components
        database = result.path[1:]
        username = result.username
        password = result.password
        hostname = result.hostname
        port = result.port
        
        # Create connection
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
            logger.debug(f"Connected to PostgreSQL: {db_version}")
        
        return connection
    except Exception as e:
        logger.error(f"Error connecting to database: {e}")
        return None

def check_column_exists(connection, table_name, column_name):
    """Check if a column exists in a table"""
    try:
        with connection.cursor() as cursor:
            cursor.execute(f"""
                SELECT column_name 
                FROM information_schema.columns 
                WHERE table_name = '{table_name}' AND column_name = '{column_name}';
            """)
            return cursor.fetchone() is not None
    except Exception as e:
        logger.error(f"Error checking if column exists: {e}")
        return False

def add_column(connection, table_name, column_name, column_type, default=None):
    """Add a column to a table if it doesn't exist"""
    try:
        # First check if column exists
        if check_column_exists(connection, table_name, column_name):
            logger.info(f"Колонка '{column_name}' вже існує, пропускаємо")
            return True
            
        with connection.cursor() as cursor:
            # Build SQL statement based on whether a default is provided
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
        connection.rollback()
        return False

def fix_database():
    """Apply all necessary database fixes"""
    # Maximum retry attempts
    max_retries = 5
    retry_delay = 2  # seconds
    
    for attempt in range(max_retries):
        try:
            connection = get_db_connection()
            if not connection:
                logger.error("Could not connect to database, retrying...")
                time.sleep(retry_delay)
                continue
                
            # Fix TelegramSession table
            logger.info("Додаємо колонку 'verification_code' до admin_panel_telegramsession")
            add_column(connection, 'admin_panel_telegramsession', 'verification_code', 'VARCHAR(255)', 'NULL')
            
            logger.info("Додаємо колонку 'password' до admin_panel_telegramsession")
            add_column(connection, 'admin_panel_telegramsession', 'password', 'VARCHAR(255)', 'NULL')
            
            logger.info("Додаємо колонку 'session_data' до admin_panel_telegramsession")
            add_column(connection, 'admin_panel_telegramsession', 'session_data', 'TEXT', 'NULL')
            
            logger.info("Додаємо колонку 'auth_token' до admin_panel_telegramsession")
            add_column(connection, 'admin_panel_telegramsession', 'auth_token', 'VARCHAR(255)', 'NULL')
            
            logger.info("Додаємо колонку 'needs_auth' до admin_panel_telegramsession")
            add_column(connection, 'admin_panel_telegramsession', 'needs_auth', 'BOOLEAN', 'FALSE')
            
            # Add any other tables or columns that need fixing here
            
            logger.info("Виправлення колонок PostgreSQL завершено")
            
            # Close connection
            connection.close()
            logger.info("Виправлення бази даних завершено успішно")
            return True
        except Exception as e:
            logger.error(f"Помилка виправлення бази даних: {e}")
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