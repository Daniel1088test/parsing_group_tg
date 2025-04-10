#!/usr/bin/env python3
"""
This is a standalone script to fix migration issues that doesn't rely on 
scripts module imports. It can be run directly from Django's manage.py shell.
"""

import os
import sys
import subprocess
import logging
from django.core.management import call_command
from django.db import connection

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(levelname)s %(asctime)s %(name)s %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S',
)
logger = logging.getLogger('direct_fix_migrations')

def fix_migrations():
    """
    Directly fix migration issues by applying a sequence of operations:
    1. Fake apply the merge migration
    2. Fake apply subsequent migrations to fix field conflicts
    3. Apply any pending migrations
    """
    try:
        logger.info("Starting direct migration fix")
        
        # Step 1: Check if the merge migration exists
        merge_migration_name = '0004_merge_20250408_1830'
        fix_fields_migration_name = '0005_fix_auth_conflict'
        
        # Apply the merge migration first
        logger.info(f"Applying merge migration: {merge_migration_name}")
        try:
            call_command('migrate', 'admin_panel', merge_migration_name, fake=True)
            logger.info("Merge migration applied with --fake")
        except Exception as e:
            logger.error(f"Error applying merge migration: {e}")
        
        # Apply the fix fields migration
        logger.info(f"Applying fix fields migration: {fix_fields_migration_name}")
        try:
            call_command('migrate', 'admin_panel', fix_fields_migration_name, fake=True)
            logger.info("Fix fields migration applied with --fake")
        except Exception as e:
            logger.error(f"Error applying fix fields migration: {e}")
        
        # Apply any pending migrations with --fake-initial
        logger.info("Applying any pending migrations with --fake-initial")
        try:
            call_command('migrate', fake_initial=True)
            logger.info("Pending migrations applied with --fake-initial")
        except Exception as e:
            logger.error(f"Error applying pending migrations: {e}")
        
        # Apply migrations for real
        logger.info("Applying migrations for real")
        try:
            call_command('migrate')
            logger.info("All migrations applied successfully")
            return True
        except Exception as e:
            logger.error(f"Error applying migrations: {e}")
            
            # Last resort: try to apply specific fixes directly to the database
            try:
                fix_database_directly()
            except Exception as db_error:
                logger.error(f"Direct database fix failed: {db_error}")
            
            return False
    except Exception as e:
        logger.error(f"Error in fix_migrations: {e}")
        return False

def fix_database_directly():
    """Last resort: Add missing columns directly with SQL if migrations fail"""
    logger.info("Attempting direct SQL fixes for missing columns")
    
    cursor = connection.cursor()
    
    # Check if columns exist and add them if missing
    # This is tailored for the specific issue we're facing
    try:
        # For SQLite
        if connection.vendor == 'sqlite':
            # Check if verification_code column exists
            cursor.execute("PRAGMA table_info(admin_panel_telegramsession)")
            columns = [col[1] for col in cursor.fetchall()]
            
            if 'verification_code' not in columns:
                logger.info("Adding verification_code column to SQLite database")
                cursor.execute("""
                    ALTER TABLE admin_panel_telegramsession
                    ADD COLUMN verification_code varchar(10) NULL
                """)
                
            if 'password' not in columns:
                logger.info("Adding password column to SQLite database")
                cursor.execute("""
                    ALTER TABLE admin_panel_telegramsession
                    ADD COLUMN password varchar(50) NULL
                """)
                
            if 'session_data' not in columns:
                logger.info("Adding session_data column to SQLite database")
                cursor.execute("""
                    ALTER TABLE admin_panel_telegramsession
                    ADD COLUMN session_data text NULL
                """)
                
        # For PostgreSQL    
        elif connection.vendor == 'postgresql':
            cursor.execute("""
                SELECT column_name FROM information_schema.columns 
                WHERE table_name = 'admin_panel_telegramsession' 
                AND column_name IN (
                    'verification_code', 'password', 'session_data'
                );
            """)
            existing_columns = [row[0] for row in cursor.fetchall()]
            
            if 'verification_code' not in existing_columns:
                logger.info("Adding verification_code column to PostgreSQL database")
                cursor.execute("""
                    ALTER TABLE admin_panel_telegramsession
                    ADD COLUMN verification_code varchar(10) NULL;
                """)
                
            if 'password' not in existing_columns:
                logger.info("Adding password column to PostgreSQL database")
                cursor.execute("""
                    ALTER TABLE admin_panel_telegramsession
                    ADD COLUMN password varchar(50) NULL;
                """)
                
            if 'session_data' not in existing_columns:
                logger.info("Adding session_data column to PostgreSQL database")
                cursor.execute("""
                    ALTER TABLE admin_panel_telegramsession
                    ADD COLUMN session_data text NULL;
                """)
        
        logger.info("Direct database fixes applied successfully")
        return True
    except Exception as e:
        logger.error(f"Error in direct database fix: {e}")
        return False

# This code can be executed in Django shell:
# python manage.py shell -c "exec(open('scripts/direct_fix_migrations.py').read())"
if __name__ == "__main__":
    fix_migrations() 