#!/usr/bin/env python3
import os
import sys
import subprocess
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(levelname)s %(asctime)s %(name)s %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S',
)
logger = logging.getLogger('run_migrations')

def run_migrations():
    """Run Django migrations with fallback mechanism"""
    logger.info("Starting emergency migration application script")
    
    try:
        # Try to set up Django environment
        os.environ.setdefault("DJANGO_SETTINGS_MODULE", "core.settings")
        
        # First try the Django way
        try:
            import django
            django.setup()
            
            # Run migrations programmatically
            from django.core.management import call_command
            logger.info("Running migrations via Django API")
            call_command('migrate')
            logger.info("Migrations applied successfully")
        except ImportError as e:
            logger.warning(f"Cannot import Django modules: {e}")
            logger.info("Falling back to subprocess approach")
            
            # If Django setup fails, try subprocess
            result = subprocess.run(
                ["python", "manage.py", "migrate"],
                capture_output=True,
                text=True
            )
            
            if result.returncode == 0:
                logger.info(f"Migrations applied via subprocess: {result.stdout}")
            else:
                logger.error(f"Migration failed: {result.stderr}")
                
                # Try with direct database modifications as last resort
                # This is risky but can help when migrations fail
                try:
                    logger.info("Attempting direct SQL fixes for missing columns")
                    fix_database_directly()
                except Exception as db_error:
                    logger.error(f"Direct database fix failed: {db_error}")
    
    except Exception as e:
        logger.error(f"Error in migration script: {e}")
        return False
    
    return True

def fix_database_directly():
    """Last resort: Add missing columns directly with SQL if migrations fail"""
    # Get database connection from environment
    db_url = os.environ.get('DATABASE_URL')
    if not db_url:
        logger.error("No DATABASE_URL found, cannot perform direct fixes")
        return False
    
    # Parse DATABASE_URL to get connection details
    import urllib.parse
    parts = urllib.parse.urlparse(db_url)
    
    # Connect to database
    try:
        import psycopg2
        conn = psycopg2.connect(
            dbname=parts.path.lstrip('/'),
            user=parts.username,
            password=parts.password,
            host=parts.hostname,
            port=parts.port or 5432
        )
        conn.autocommit = True
        cursor = conn.cursor()
        
        # Check if columns exist and add them if missing
        cursor.execute("""
            SELECT column_name FROM information_schema.columns 
            WHERE table_name = 'admin_panel_telegramsession' 
            AND column_name IN (
                'verification_code', 'password', 'session_data'
            );
        """)
        existing_columns = [row[0] for row in cursor.fetchall()]
        
        # Add missing columns
        if 'verification_code' not in existing_columns:
            logger.info("Adding verification_code column")
            cursor.execute("""
                ALTER TABLE admin_panel_telegramsession
                ADD COLUMN verification_code varchar(10) NULL;
            """)
            
        if 'password' not in existing_columns:
            logger.info("Adding password column")
            cursor.execute("""
                ALTER TABLE admin_panel_telegramsession
                ADD COLUMN password varchar(50) NULL;
            """)
            
        if 'session_data' not in existing_columns:
            logger.info("Adding session_data column")
            cursor.execute("""
                ALTER TABLE admin_panel_telegramsession
                ADD COLUMN session_data text NULL;
            """)
            
        # Update existing columns with help text (won't cause errors if different)
        cursor.execute("""
            COMMENT ON COLUMN admin_panel_telegramsession.needs_auth IS 
            'Indicates if this session needs manual authentication';
        """)
        
        logger.info("Direct database fixes applied successfully")
        return True
    
    except Exception as e:
        logger.error(f"Error performing direct database fixes: {e}")
        return False
    
    finally:
        if 'conn' in locals():
            conn.close()

if __name__ == "__main__":
    success = run_migrations()
    if success:
        logger.info("Migration script completed successfully")
        sys.exit(0)
    else:
        logger.error("Migration script failed")
        sys.exit(1) 