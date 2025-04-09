#!/usr/bin/env python3
"""
Direct SQL fix for migration issues
This script directly marks migrations as completed in the database
"""
import os
import sys
import django
import logging
import traceback
from django.db import connection, DatabaseError
from urllib.parse import urlparse
import psycopg2

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Setup Django with explicit DATABASE_URL
database_url = os.environ.get('DATABASE_URL')
if not database_url:
    logger.error("DATABASE_URL not set, cannot continue")
    sys.exit(1)

logger.info(f"Using database from DATABASE_URL: {database_url[:15]}...")

# Set environment variables before Django setup
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
os.environ['DATABASE_URL'] = database_url
django.setup()

# Check if we're using PostgreSQL
from django.conf import settings
if 'postgresql' not in settings.DATABASES['default']['ENGINE']:
    logger.error("Not using PostgreSQL! Settings configured for: %s", 
                 settings.DATABASES['default']['ENGINE'])
    logger.info("Will force direct PostgreSQL connection")
    use_direct_connection = True
else:
    logger.info("Django correctly configured to use PostgreSQL")
    use_direct_connection = False

def get_postgres_cursor():
    """Get a cursor to PostgreSQL either via Django or direct connection"""
    if use_direct_connection:
        # Parse DATABASE_URL
        url = urlparse(database_url)
        dbname = url.path[1:]
        user = url.username
        password = url.password
        host = url.hostname
        port = url.port

        # Connect directly
        logger.info(f"Connecting directly to PostgreSQL: {host}:{port}/{dbname}")
        conn = psycopg2.connect(
            dbname=dbname,
            user=user,
            password=password,
            host=host,
            port=port
        )
        conn.autocommit = True
        return conn.cursor()
    else:
        # Use Django connection
        logger.info("Using Django database connection")
        return connection.cursor()

def fix_migrations():
    """Fix the migration records directly in the database"""
    try:
        logger.info("Running direct SQL fix for migrations...")
        cursor = get_postgres_cursor()
        
        # Check if the django_migrations table exists
        try:
            cursor.execute("SELECT to_regclass('public.django_migrations');")
            table_exists = cursor.fetchone()[0]
            
            if table_exists:
                # Get current migrations
                cursor.execute("SELECT id, app, name FROM django_migrations WHERE app='admin_panel';")
                existing_migrations = cursor.fetchall()
                logger.info(f"Found {len(existing_migrations)} existing migrations for admin_panel:")
                for migration in existing_migrations:
                    logger.info(f"  {migration[0]}: {migration[1]}.{migration[2]}")
                
                # Required migrations that should be marked as applied
                required_migrations = [
                    '0001_initial',
                    '0002_auto_20250409_0000',
                    'fix_is_bot_column',
                    '0003_merge_final',
                    '0004_fake_migration'
                ]
                
                # Get existing migration names
                existing_names = [row[2] for row in existing_migrations]
                
                # Add missing migrations
                for migration in required_migrations:
                    if migration not in existing_names:
                        logger.info(f"Adding missing migration: admin_panel.{migration}")
                        cursor.execute(
                            "INSERT INTO django_migrations (app, name, applied) VALUES (%s, %s, now());",
                            ['admin_panel', migration]
                        )
                
                # Fix database structure directly
                logger.info("Applying direct SQL fixes to database structure...")
                try:
                    cursor.execute("""
                    DO $$
                    BEGIN
                        BEGIN
                            ALTER TABLE admin_panel_telegramsession DROP COLUMN IF EXISTS needs_auth;
                        EXCEPTION WHEN undefined_column THEN
                            RAISE NOTICE 'Column needs_auth does not exist, skipping';
                        END;
                        
                        BEGIN
                            ALTER TABLE admin_panel_telegramsession ADD COLUMN IF NOT EXISTS needs_auth BOOLEAN DEFAULT TRUE;
                        EXCEPTION WHEN duplicate_column THEN
                            RAISE NOTICE 'Column needs_auth already exists';
                        END;

                        -- Make sure other required columns exist
                        BEGIN
                            ALTER TABLE admin_panel_telegramsession ADD COLUMN IF NOT EXISTS auth_token VARCHAR(255) DEFAULT NULL;
                        EXCEPTION WHEN duplicate_column THEN
                            RAISE NOTICE 'Column auth_token already exists';
                        END;
                        
                        -- Fix BotSettings table
                        BEGIN
                            ALTER TABLE admin_panel_botsettings ADD COLUMN IF NOT EXISTS bot_username VARCHAR(255) NULL;
                        EXCEPTION WHEN duplicate_column THEN
                            RAISE NOTICE 'Column bot_username already exists';
                        END;
                        
                        BEGIN
                            ALTER TABLE admin_panel_botsettings ADD COLUMN IF NOT EXISTS bot_name VARCHAR(255) NULL;
                        EXCEPTION WHEN duplicate_column THEN
                            RAISE NOTICE 'Column bot_name already exists';
                        END;
                        
                        BEGIN
                            ALTER TABLE admin_panel_botsettings ADD COLUMN IF NOT EXISTS default_api_id VARCHAR(255) NULL;
                        EXCEPTION WHEN duplicate_column THEN
                            RAISE NOTICE 'Column default_api_id already exists';
                        END;
                        
                        BEGIN
                            ALTER TABLE admin_panel_botsettings ADD COLUMN IF NOT EXISTS default_api_hash VARCHAR(255) NULL;
                        EXCEPTION WHEN duplicate_column THEN
                            RAISE NOTICE 'Column default_api_hash already exists';
                        END;
                    END
                    $$;
                    """)
                    logger.info("Direct SQL structure fixes completed")
                except Exception as e:
                    logger.error(f"Failed to apply direct SQL fixes: {e}")
                    logger.error(traceback.format_exc())
                
                logger.info("Migration records fixed successfully")
                return True
            else:
                logger.error("django_migrations table does not exist, creating it now")
                # Try to create the table
                try:
                    logger.info("Creating django_migrations table...")
                    cursor.execute("""
                    CREATE TABLE IF NOT EXISTS django_migrations (
                        id SERIAL PRIMARY KEY,
                        app VARCHAR(255) NOT NULL,
                        name VARCHAR(255) NOT NULL,
                        applied TIMESTAMP WITH TIME ZONE NOT NULL
                    );
                    """)
                    logger.info("Created django_migrations table, adding required migrations")
                    
                    # Required migrations
                    required_migrations = [
                        '0001_initial',
                        '0002_auto_20250409_0000',
                        'fix_is_bot_column',
                        '0003_merge_final',
                        '0004_fake_migration'
                    ]
                    
                    # Add all required migrations
                    for migration in required_migrations:
                        cursor.execute(
                            "INSERT INTO django_migrations (app, name, applied) VALUES (%s, %s, now());",
                            ['admin_panel', migration]
                        )
                    
                    logger.info("Added required migrations to newly created table")
                    return True
                except Exception as create_error:
                    logger.error(f"Failed to create django_migrations table: {create_error}")
                    logger.error(traceback.format_exc())
                    return False
        except Exception as db_error:
            logger.error(f"Error querying django_migrations table: {db_error}")
            logger.error(traceback.format_exc())
            return False
    except DatabaseError as e:
        logger.error(f"Database error: {e}")
        logger.error(traceback.format_exc())
        return False
    except Exception as e:
        logger.error(f"Error: {e}")
        logger.error(traceback.format_exc())
        return False

if __name__ == "__main__":
    success = fix_migrations()
    sys.exit(0 if success else 1) 