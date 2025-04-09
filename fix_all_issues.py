#!/usr/bin/env python3
"""
Comprehensive fix script for Telegram Bot and Django project
Fixes common issues and ensures proper database and environment setup
"""
import os
import sys
import logging
import subprocess
import importlib.util
import traceback
import time

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('fix_all_issues.log', encoding='utf-8'),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger('fix_all_issues')

def run_fix_script(script_name, description):
    """Run a fix script and handle errors"""
    logger.info(f"Running {description}...")
    
    try:
        # Check if the script exists
        if not os.path.exists(script_name):
            logger.warning(f"Script {script_name} not found, skipping")
            return False
        
        # Run the script as a module if possible
        module_name = os.path.splitext(script_name)[0]
        try:
            spec = importlib.util.spec_from_file_location(module_name, script_name)
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
            
            # Call main() function if it exists
            if hasattr(module, 'main'):
                module.main()
                logger.info(f"Successfully ran {script_name}")
                return True
        except Exception as import_error:
            logger.warning(f"Error importing {script_name} as module: {import_error}")
            
        # Fall back to subprocess
        logger.info(f"Running {script_name} as subprocess...")
        subprocess.check_call([sys.executable, script_name])
        logger.info(f"Successfully ran {script_name} as subprocess")
        return True
    except Exception as e:
        logger.error(f"Error running {script_name}: {e}")
        logger.error(traceback.format_exc())
        return False

def check_install_dependencies():
    """Check and install missing dependencies"""
    logger.info("Checking and installing dependencies...")
    missing_packages = []
    
    # List of required packages
    required_packages = [
        'django',
        'aiogram',
        'psycopg2-binary',
        'dj-database-url',
        'whitenoise',
        'telethon',
        'qrcode',
        'pillow',
        'requests',
        'async-timeout'
    ]
    
    # Check each package
    for package in required_packages:
        try:
            importlib.import_module(package)
            logger.info(f"Package {package} is already installed")
        except ImportError:
            logger.warning(f"Package {package} is missing")
            missing_packages.append(package)
    
    # Install missing packages
    if missing_packages:
        logger.warning(f"Installing missing packages: {', '.join(missing_packages)}")
        try:
            subprocess.check_call([sys.executable, "-m", "pip", "install"] + missing_packages)
            logger.info("All missing packages have been installed")
            return True
        except Exception as e:
            logger.error(f"Error installing packages: {e}")
            return False
    return True

def fix_migrations_sql():
    """Fix SQL syntax in migration files"""
    logger.info("Fixing SQL syntax in migration files...")
    
    try:
        # Get migration directories
        migration_dirs = [
            os.path.join('admin_panel', 'migrations'),
        ]
        
        fixed_count = 0
        for migrations_dir in migration_dirs:
            if not os.path.exists(migrations_dir):
                logger.warning(f"Migrations directory not found: {migrations_dir}")
                continue
                
            for migration_file in os.listdir(migrations_dir):
                if not migration_file.endswith('.py'):
                    continue
                    
                full_path = os.path.join(migrations_dir, migration_file)
                with open(full_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                # Fix incorrect DO 1 BEGIN syntax in SQL
                if 'DO 1 BEGIN' in content:
                    new_content = content.replace('DO 1 BEGIN', 'DO $$ BEGIN')
                    new_content = new_content.replace('END 1;', 'END $$;')
                    
                    with open(full_path, 'w', encoding='utf-8') as f:
                        f.write(new_content)
                    
                    fixed_count += 1
                    logger.info(f"Fixed SQL syntax in {full_path}")
        
        if fixed_count > 0:
            logger.info(f"Fixed SQL syntax in {fixed_count} migration files")
        else:
            logger.info("No SQL syntax issues found in migration files")
        
        return True
    except Exception as e:
        logger.error(f"Error fixing migrations: {e}")
        logger.error(traceback.format_exc())
        return False

def fix_database_connection():
    """Fix database connection issues"""
    logger.info("Fixing database connection...")
    
    try:
        # Setup Django
        os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
        
        # Check if DATABASE_URL is set and valid
        database_url = os.environ.get('DATABASE_URL', '')
        if database_url and ('postgres' in database_url or 'sqlite' in database_url):
            logger.info(f"Using database URL: {database_url.split('@')[0]}...")
        else:
            # Check for Railway PostgreSQL environment variables
            pghost = os.environ.get('PGHOST')
            pgport = os.environ.get('PGPORT')
            pgdatabase = os.environ.get('PGDATABASE')
            pguser = os.environ.get('PGUSER')
            pgpassword = os.environ.get('PGPASSWORD')
            
            if all([pghost, pgport, pgdatabase, pguser, pgpassword]):
                # Construct DATABASE_URL
                database_url = f"postgresql://{pguser}:{pgpassword}@{pghost}:{pgport}/{pgdatabase}"
                os.environ['DATABASE_URL'] = database_url
                logger.info(f"Set DATABASE_URL from PG* environment variables")
            else:
                # Default to SQLite
                db_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'db.sqlite3')
                database_url = f"sqlite:///{db_path}"
                os.environ['DATABASE_URL'] = database_url
                logger.info(f"No database configuration found, defaulting to SQLite at {db_path}")
        
        # Initialize Django
        import django
        django.setup()
        
        # Test database connection
        from django.db import connection
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
            result = cursor.fetchone()
            
        if result and result[0] == 1:
            logger.info("Database connection successful")
            return True
        else:
            logger.error("Database connection test failed")
            return False
    except Exception as e:
        logger.error(f"Error fixing database connection: {e}")
        logger.error(traceback.format_exc())
        return False

def ensure_bot_environment():
    """Ensure bot environment variables are set"""
    logger.info("Setting up bot environment...")
    
    try:
        # Check and set BOT_TOKEN
        bot_token = os.environ.get('BOT_TOKEN', '')
        if not bot_token or len(bot_token) < 30:
            # Try to get from config
            try:
                from tg_bot.config import TOKEN_BOT
                if TOKEN_BOT and len(TOKEN_BOT) > 30:
                    os.environ['BOT_TOKEN'] = TOKEN_BOT
                    logger.info(f"Set BOT_TOKEN from config.py: {TOKEN_BOT[:8]}...")
                else:
                    # Use hardcoded token
                    os.environ['BOT_TOKEN'] = "8102516142:AAFTsVXXujHHKoX2KZGqZXBHPBznfgh7kg0"
                    logger.info("Set BOT_TOKEN to hardcoded value")
            except ImportError:
                # Use hardcoded token
                os.environ['BOT_TOKEN'] = "8102516142:AAFTsVXXujHHKoX2KZGqZXBHPBznfgh7kg0"
                logger.info("Set BOT_TOKEN to hardcoded value (config.py not found)")
        else:
            logger.info(f"Using existing BOT_TOKEN: {bot_token[:8]}...")
        
        # Check and set BOT_USERNAME
        bot_username = os.environ.get('BOT_USERNAME', '')
        if not bot_username:
            # Set default
            os.environ['BOT_USERNAME'] = "chan_parsing_mon_bot"
            logger.info("Set BOT_USERNAME to default value")
        
        # Check and set API_ID and API_HASH for Telegram client
        api_id = os.environ.get('API_ID', '')
        api_hash = os.environ.get('API_HASH', '')
        
        if not api_id or not api_hash:
            # Set defaults
            os.environ['API_ID'] = "19840544"
            os.environ['API_HASH'] = "c839f28bad345082329ec086fca021fa"
            logger.info("Set API_ID and API_HASH to default values")
        
        return True
    except Exception as e:
        logger.error(f"Error setting up bot environment: {e}")
        logger.error(traceback.format_exc())
        return False

def main():
    """Main function to fix all issues"""
    logger.info("=== Starting comprehensive fix script ===")
    
    # Check and install dependencies
    check_install_dependencies()
    
    # Fix database connection
    fix_database_connection()
    
    # Fix migrations
    fix_migrations_sql()
    
    # Ensure bot environment variables
    ensure_bot_environment()
    
    # Run session fix script
    run_fix_script('fix_session_migration.py', 'Telegram session model fix')
    
    # Run admin query fix script
    run_fix_script('fix_admin_query.py', 'Admin query fix')
    
    # Run token check script
    run_fix_script('token_check.py', 'Bot token check')
    
    # Apply migrations if needed
    try:
        logger.info("Applying migrations...")
        os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
        import django
        django.setup()
        from django.core.management import call_command
        call_command('migrate', interactive=False)
        logger.info("Migrations applied successfully")
    except Exception as e:
        logger.error(f"Error applying migrations: {e}")
    
    logger.info("=== Fix script completed ===")
    return True

if __name__ == "__main__":
    try:
        success = main()
        sys.exit(0 if success else 1)
    except Exception as e:
        logger.critical(f"Unhandled error: {e}")
        logger.critical(traceback.format_exc())
        sys.exit(1) 