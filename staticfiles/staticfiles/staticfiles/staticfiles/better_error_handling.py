#!/usr/bin/env python
import os
import sys
import django
import logging
from django.db import connection, reset_queries

# Setup Django
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Enable query logging
from django.conf import settings
settings.DEBUG = True

# Import models
from admin_panel.models import TelegramSession, Category, Channel, Message

def analyze_query():
    """Try to execute a query with debug info"""
    try:
        logger.info("Analyzing model definition...")
        # Print the model fields
        for field in TelegramSession._meta.fields:
            logger.info(f"Model field: {field.name} ({field.__class__.__name__})")
        
        # Try a simple query
        reset_queries()
        logger.info("Trying a simple TelegramSession query...")
        sessions = TelegramSession.objects.all()
        logger.info(f"Found {len(sessions)} sessions")
        
        # Print the executed query
        for query in connection.queries:
            logger.info(f"SQL: {query['sql']}")
    except Exception as e:
        logger.error(f"Error during query: {e}")
        
        # Try to get more details about the error
        import traceback
        logger.error(traceback.format_exc())

def check_column_existence():
    """Check if specific columns exist in the database"""
    try:
        logger.info("Checking column existence in database...")
        with connection.cursor() as cursor:
            cursor.execute("PRAGMA table_info(admin_panel_telegramsession)")
            columns = {info[1]: info for info in cursor.fetchall()}
            logger.info(f"Database columns: {', '.join(columns.keys())}")
            
            # Check specific columns
            for col in ['is_bot', 'session_name', 'session_string']:
                if col in columns:
                    logger.info(f"Column '{col}' exists in database")
                else:
                    logger.warning(f"Column '{col}' does NOT exist in database")
    except Exception as e:
        logger.error(f"Error checking columns: {e}")

def fix_database_schema():
    """Apply fixes to the database schema"""
    try:
        logger.info("Fixing database schema...")
        with connection.cursor() as cursor:
            # Fix is_bot column
            try:
                cursor.execute("""
                    -- Rename the existing is_bot column if it's causing problems
                    ALTER TABLE admin_panel_telegramsession RENAME COLUMN is_bot TO is_bot_old;
                """)
                logger.info("Renamed problematic is_bot column")
                
                # Create a new is_bot column with correct definition
                cursor.execute("""
                    ALTER TABLE admin_panel_telegramsession 
                    ADD COLUMN is_bot BOOLEAN DEFAULT 0;
                """)
                logger.info("Added new is_bot column with correct definition")
            except Exception as e:
                logger.error(f"Error fixing is_bot column: {e}")
    except Exception as e:
        logger.error(f"Error in schema fix: {e}")

if __name__ == "__main__":
    # First, check column existence
    check_column_existence()
    
    # Then analyze the query
    analyze_query()
    
    # Ask user if they want to apply fixes
    user_input = input("\nDo you want to apply schema fixes? (y/n): ")
    if user_input.lower() == 'y':
        fix_database_schema()
        
        # Check if fix worked
        analyze_query() 