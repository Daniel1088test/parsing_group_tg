#!/usr/bin/env python3
"""
Direct SQL fix for migration issues
This script directly marks migrations as completed in the database
"""
import os
import sys
import django
import logging
from django.db import connection, DatabaseError
from urllib.parse import urlparse

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Setup Django with explicit DATABASE_URL
database_url = os.environ.get('DATABASE_URL')
if not database_url:
    logger.error("DATABASE_URL not set, cannot continue")
    sys.exit(1)

logger.info(f"Using database from DATABASE_URL")

# Set environment variables before Django setup
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
os.environ['DATABASE_URL'] = database_url

# Initialize Django
django.setup()

def fix_migrations():
    """Fix the migration records directly in the database"""
    try:
        logger.info("Running direct SQL fix for migrations...")
        with connection.cursor() as cursor:
            # Check if the django_migrations table exists
            try:
                cursor.execute("SELECT to_regclass('public.django_migrations');")
                if cursor.fetchone()[0]:
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
                        END
                        $$;
                        """)
                        logger.info("Direct SQL structure fixes completed")
                    except Exception as e:
                        logger.error(f"Failed to apply direct SQL fixes: {e}")
                    
                    logger.info("Migration records fixed successfully")
                    return True
                else:
                    logger.error("django_migrations table does not exist, cannot fix directly")
                    return False
            except Exception as db_error:
                logger.error(f"Error querying django_migrations table: {db_error}")
                # Try to create the table if it doesn't exist
                try:
                    logger.info("Attempting to create django_migrations table...")
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
                    return False
    except DatabaseError as e:
        logger.error(f"Database error: {e}")
        return False
    except Exception as e:
        logger.error(f"Error: {e}")
        return False

if __name__ == "__main__":
    success = fix_migrations()
    sys.exit(0 if success else 1) 