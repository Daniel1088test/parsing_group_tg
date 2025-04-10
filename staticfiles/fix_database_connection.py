#!/usr/bin/env python3
"""
Script to fix database connection and initialization issues
"""
import os
import sys
import logging
import django
import psycopg2
import traceback
import re
from pathlib import Path

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Replace the standard StreamHandler with one that has proper encoding
for handler in logger.handlers:
    if isinstance(handler, logging.StreamHandler):
        logger.removeHandler(handler)

# Add new handler with proper encoding
console_handler = logging.StreamHandler(sys.stdout)
console_handler.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))
logger.addHandler(console_handler)

def setup_environment():
    """Set up environment variables for database connection"""
    # Check if running in Railway
    is_railway = os.environ.get('RAILWAY_ENVIRONMENT') is not None or os.environ.get('RAILWAY_SERVICE_NAME') is not None
    
    if is_railway:
        logger.info("Running in Railway environment")
        # Make sure required PostgreSQL variables are set
        os.environ.setdefault('PGHOST', 'postgres.railway.internal')
        os.environ.setdefault('PGPORT', '5432')
        os.environ.setdefault('PGUSER', 'postgres')
        os.environ.setdefault('PGDATABASE', 'railway')
        
        # Set Django settings
        os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
    else:
        logger.info("Running in local environment")
        # Set defaults for local development
        os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
    
    # Bot tokens - ensure they're always available
    os.environ.setdefault('BOT_TOKEN', '8102516142:AAFTsVXXujHHKoX2KZGqZXBHPBznfgh7kg0')
    os.environ.setdefault('BOT_USERNAME', 'chan_parsing_mon_bot')
    
    logger.info("Environment variables set")

def test_database_connection():
    """Test the database connection and show detailed info"""
    try:
        # Get connection parameters from environment
        host = os.environ.get('PGHOST', 'localhost')
        port = os.environ.get('PGPORT', '5432')
        user = os.environ.get('PGUSER', 'postgres')
        password = os.environ.get('PGPASSWORD', '')
        database = os.environ.get('PGDATABASE', 'postgres')
        
        logger.info(f"Connecting to PostgreSQL: {host}:{port}/{database}")
        
        # Try to connect
        conn = psycopg2.connect(
            host=host,
            port=port,
            user=user,
            password=password,
            database=database
        )
        
        # Get server info
        cursor = conn.cursor()
        cursor.execute("SELECT version();")
        version = cursor.fetchone()[0]
        
        logger.info(f"[OK] PostgreSQL connection successful: {version}")
        
        # Test if tables exist
        cursor.execute("""
            SELECT table_name 
            FROM information_schema.tables 
            WHERE table_schema='public'
        """)
        tables = cursor.fetchall()
        
        if tables:
            logger.info(f"Found {len(tables)} tables in the database:")
            for table in tables:
                logger.info(f"  - {table[0]}")
        else:
            logger.warning("No tables found in the database. This might indicate a fresh installation.")
        
        conn.close()
        return True
    except Exception as e:
        logger.error(f"Database connection error: {e}")
        logger.error(traceback.format_exc())
        return False

def fix_invalid_sql():
    """Fix any invalid SQL in migration files"""
    try:
        migrations_root = Path('admin_panel/migrations')
        
        if not migrations_root.exists():
            logger.warning("No migrations directory found at 'admin_panel/migrations'")
            return False
        
        # Look for SQL files and migration files
        migration_files = list(migrations_root.glob('*.py'))
        
        logger.info(f"Found {len(migration_files)} migration files")
        
        # Check each migration file for potentially problematic SQL
        for file_path in migration_files:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Check for SQL statements with line numbers at the beginning
            # This is a common issue with copied SQL
            if re.search(r'migrations\.RunSQL\([\'"].*?^\s*\d+', content, re.MULTILINE | re.DOTALL):
                logger.info(f"Found potentially problematic SQL in {file_path}")
                
                # Fix the SQL by removing line numbers
                updated_content = re.sub(
                    r'(migrations\.RunSQL\([\'"].*?)^\s*\d+\s*', 
                    r'\1', 
                    content, 
                    flags=re.MULTILINE | re.DOTALL
                )
                
                # Write the fixed content
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(updated_content)
                
                logger.info(f"[OK] Fixed SQL in {file_path}")
        
        return True
    except Exception as e:
        logger.error(f"Error fixing SQL files: {e}")
        logger.error(traceback.format_exc())
        return False

def create_missing_tables():
    """Create missing tables by running migrations"""
    try:
        # Initialize Django
        django.setup()
        
        # Run makemigrations and migrate
        from django.core.management import call_command
        
        logger.info("Running makemigrations...")
        call_command('makemigrations')
        
        logger.info("Running migrate...")
        call_command('migrate')
        
        logger.info("[OK] Database migrations applied")
        return True
    except Exception as e:
        logger.error(f"Error running migrations: {e}")
        logger.error(traceback.format_exc())
        return False

def fix_model_fields():
    """Fix any issues with model fields"""
    try:
        # Check models.py for issues
        models_path = Path('admin_panel/models.py')
        
        if not models_path.exists():
            logger.warning("Could not find admin_panel/models.py")
            return False
        
        with open(models_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Check for common issues and fix them
        
        # Fix 1: Make sure telegram_channel_id is nullable to fix migration issues
        if 'telegram_channel_id' in content and 'null=True' not in content:
            content = re.sub(
                r'(telegram_channel_id\s*=\s*models\.BigInteger\w*\([^)]*\))',
                r'\1, null=True, blank=True',
                content
            )
            logger.info("Fixed telegram_channel_id field to be nullable")
        
        # Fix 2: Fix any non-nullable fields that should be nullable
        modified = False
        for field in ['username', 'title', 'description', 'link']:
            pattern = rf'({field}\s*=\s*models\.Char\w*\([^)]*\))'
            replacement = r'\1, null=True, blank=True'
            
            if field in content and re.search(pattern, content) and 'null=True' not in re.search(pattern, content).group(0):
                content = re.sub(pattern, replacement, content)
                logger.info(f"Fixed {field} field to be nullable")
                modified = True
        
        if modified:
            # Write the updated content
            with open(models_path, 'w', encoding='utf-8') as f:
                f.write(content)
            
            logger.info("[OK] Updated model fields in admin_panel/models.py")
        
        return True
    except Exception as e:
        logger.error(f"Error fixing model fields: {e}")
        logger.error(traceback.format_exc())
        return False

def initialize_bot_settings():
    """Initialize the BotSettings in the database"""
    try:
        # Initialize Django
        django.setup()
        
        # Import needed models
        from django.db import connection
        from django.conf import settings
        
        # Check if BotSettings table exists
        with connection.cursor() as cursor:
            cursor.execute("""
                SELECT EXISTS (
                    SELECT FROM information_schema.tables 
                    WHERE table_name = 'admin_panel_botsettings'
                );
            """)
            table_exists = cursor.fetchone()[0]
        
        if not table_exists:
            logger.warning("BotSettings table does not exist, will be created with migrations")
            return False
        
        # Check if there are any records in BotSettings
        with connection.cursor() as cursor:
            cursor.execute("SELECT COUNT(*) FROM admin_panel_botsettings")
            count = cursor.fetchone()[0]
        
        # If no records, initialize with default values
        if count == 0:
            logger.info("No BotSettings found, creating default entry")
            
            # Import the BotSettings model
            from admin_panel.models import BotSettings
            
            # Create default settings
            BotSettings.objects.create(
                bot_token=os.environ.get('BOT_TOKEN', '8102516142:AAFTsVXXujHHKoX2KZGqZXBHPBznfgh7kg0'),
                bot_username=os.environ.get('BOT_USERNAME', 'chan_parsing_mon_bot'),
                bot_name="Channel Parser Bot",
                menu_style="buttons"
            )
            
            logger.info("[OK] Created default BotSettings record")
        else:
            logger.info(f"Found {count} BotSettings records, no initialization needed")
        
        # Update the bot token if it doesn't match the environment
        from admin_panel.models import BotSettings
        bot_settings = BotSettings.objects.first()
        if bot_settings and bot_settings.bot_token != os.environ.get('BOT_TOKEN'):
            bot_settings.bot_token = os.environ.get('BOT_TOKEN', '8102516142:AAFTsVXXujHHKoX2KZGqZXBHPBznfgh7kg0')
            bot_settings.bot_username = os.environ.get('BOT_USERNAME', 'chan_parsing_mon_bot')
            bot_settings.save()
            logger.info(f"[OK] Updated BotSettings with current BOT_TOKEN and BOT_USERNAME")
        
        return True
    except Exception as e:
        logger.error(f"Error initializing BotSettings: {e}")
        logger.error(traceback.format_exc())
        return False

def fix_urls():
    """Fix URL patterns that cause warnings"""
    try:
        urls_path = Path('core/urls.py')
        
        if not urls_path.exists():
            logger.warning("Could not find core/urls.py")
            return False
        
        with open(urls_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Fix URL patterns with leading slashes
        if re.search(r"url\(r'\^/", content) or re.search(r"re_path\(r'\^/", content) or re.search(r"path\('\^/", content):
            # Remove leading slashes from URL patterns
            content = re.sub(r"(url\(r'\^)/", r"\1", content)
            content = re.sub(r"(re_path\(r'\^)/", r"\1", content)
            content = re.sub(r"(path\('\^)/", r"\1", content)
            
            # Write the updated content
            with open(urls_path, 'w', encoding='utf-8') as f:
                f.write(content)
            
            logger.info("[OK] Fixed URL patterns with leading slashes in core/urls.py")
        
        return True
    except Exception as e:
        logger.error(f"Error fixing URL patterns: {e}")
        logger.error(traceback.format_exc())
        return False

def reset_migrations_if_needed():
    """Reset migrations if they are causing issues"""
    try:
        # Initialize Django
        django.setup()
        
        # Check if there are any failed migrations
        with django.db.connection.cursor() as cursor:
            try:
                cursor.execute("SELECT EXISTS (SELECT FROM information_schema.tables WHERE table_name = 'django_migrations')")
                table_exists = cursor.fetchone()[0]
                
                if not table_exists:
                    logger.warning("django_migrations table does not exist, likely a fresh database")
                    return False
                
                # Check if there were recent migration attempts
                cursor.execute("SELECT COUNT(*) FROM django_migrations WHERE app = 'admin_panel'")
                migration_count = cursor.fetchone()[0]
                
                if migration_count == 0:
                    logger.warning("No admin_panel migrations found in the database")
                    return False
            except Exception as e:
                logger.error(f"Error checking migrations: {e}")
                return False
        
        # If we got here, migrations table exists and has records
        # Now check if we need to reset migrations due to errors
        migrations_dir = Path('admin_panel/migrations')
        migration_files = list(migrations_dir.glob('*.py'))
        
        # Skip __init__.py
        migration_files = [f for f in migration_files if f.name != '__init__.py']
        
        if len(migration_files) > migration_count + 3:
            logger.warning(f"Found {len(migration_files)} migration files but only {migration_count} applied. Migration files might be out of sync.")
            
            # Backup existing migrations
            backup_dir = migrations_dir / 'backup'
            backup_dir.mkdir(exist_ok=True)
            
            for f in migration_files:
                if f.name != '__init__.py':
                    try:
                        shutil.copy(f, backup_dir / f.name)
                        logger.info(f"Backed up {f.name}")
                    except Exception as e:
                        logger.error(f"Error backing up {f.name}: {e}")
            
            # Create a new initial migration
            from django.core.management import call_command
            
            # Remove old migration files
            for f in migration_files:
                if f.name != '__init__.py':
                    try:
                        f.unlink()
                        logger.info(f"Removed {f.name}")
                    except Exception as e:
                        logger.error(f"Error removing {f.name}: {e}")
            
            # Make new migrations
            call_command('makemigrations', 'admin_panel')
            logger.info("[OK] Reset migrations for admin_panel app")
            
            # Fake initial migration
            call_command('migrate', 'admin_panel', '--fake-initial')
            logger.info("[OK] Faked initial migration")
            
            return True
        
        logger.info("Migrations appear to be in sync, no reset needed")
        return True
    except Exception as e:
        logger.error(f"Error resetting migrations: {e}")
        logger.error(traceback.format_exc())
        return False
        
def main():
    """Main function to fix database connection and initialization issues"""
    logger.info("=== Starting database connection and initialization fix ===")
    
    # Setup environment
    setup_environment()
    
    # Test database connection
    if not test_database_connection():
        logger.error("Database connection failed, please check your configuration")
        return False
    
    # Fix invalid SQL in migrations
    fix_invalid_sql()
    
    # Fix model fields
    fix_model_fields()
    
    # Fix URL patterns
    fix_urls()
    
    # Create missing tables
    create_missing_tables()
    
    # Initialize BotSettings
    initialize_bot_settings()
    
    # Reset migrations if needed
    reset_migrations_if_needed()
    
    logger.info("=== Database connection and initialization fix completed ===")
    logger.info("Please restart your application to apply the changes")
    
    return True

if __name__ == "__main__":
    try:
        import shutil
        import django.db
        main()
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        logger.error(traceback.format_exc())
    sys.exit(0) 