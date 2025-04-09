#!/usr/bin/env python3
"""
Emergency fix script for Telegram bot connection issues
This script will:
1. Test connection to Telegram API
2. Verify the bot token is valid
3. Create proper BotSettings in database
4. Force update the token in all necessary locations
"""
import os
import sys
import time
import asyncio
import logging
import traceback
from datetime import datetime

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('fix_bot_connection.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger('fix_bot_connection')

# Initialize Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
try:
    import django
    django.setup()
    logger.info("Django initialized successfully")
except Exception as e:
    logger.error(f"Failed to initialize Django: {e}")
    sys.exit(1)

# Import Django models
try:
    from django.db import connection, transaction
    from django.db.utils import OperationalError, ProgrammingError
    from admin_panel.models import BotSettings
    from asgiref.sync import sync_to_async  # Import sync_to_async
    logger.info("Models imported successfully")
except Exception as e:
    logger.error(f"Failed to import models: {e}")
    sys.exit(1)

# Check environment for token
def get_bot_token():
    """Get bot token from various sources"""
    token = os.environ.get('BOT_TOKEN')
    if token:
        logger.info("Using BOT_TOKEN from environment")
        return token
    
    # Try to get token from bot_token.env file
    if os.path.exists('bot_token.env'):
        try:
            with open('bot_token.env', 'r') as f:
                content = f.read().strip()
                if content.startswith('BOT_TOKEN='):
                    token = content.split('=', 1)[1].strip()
                    os.environ['BOT_TOKEN'] = token
                    logger.info(f"Using BOT_TOKEN from bot_token.env")
                    return token
        except Exception as e:
            logger.error(f"Error reading bot_token.env: {e}")
    
    # Try to get token from config.py
    try:
        from tg_bot.config import TOKEN_BOT
        if TOKEN_BOT:
            os.environ['BOT_TOKEN'] = TOKEN_BOT
            logger.info(f"Using BOT_TOKEN from config.py")
            return TOKEN_BOT
    except Exception as e:
        logger.error(f"Error loading token from config.py: {e}")
    
    # Hardcoded token as last resort
    hardcoded_token = "7923260865:AAGYew9JnOJV6hz0LGeRCb1kS6AejHoX61g"
    logger.warning(f"Using hardcoded token as last resort")
    os.environ['BOT_TOKEN'] = hardcoded_token
    return hardcoded_token

async def verify_token(token):
    """Test if the token is valid by connecting to Telegram API"""
    logger.info(f"Testing token: {token[:5]}...{token[-5:]}")
    
    try:
        # Import aiogram
        from aiogram import Bot
        bot = Bot(token=token)
        
        # Test connection by getting bot info
        start_time = time.time()
        bot_info = await bot.get_me()
        elapsed = time.time() - start_time
        
        logger.info(f"✅ Token is valid! Bot: @{bot_info.username} (ID: {bot_info.id})")
        logger.info(f"API response time: {elapsed:.2f} seconds")
        
        # Write verification flag
        with open('bot_verified.flag', 'w') as f:
            f.write(f"{bot_info.id}:{bot_info.username}")
        logger.info("Created bot_verified.flag")
        
        return True, bot_info
    except Exception as e:
        logger.error(f"❌ Token verification failed: {e}")
        logger.error(traceback.format_exc())
        return False, None

# Make this function synchronous so we can wrap it with sync_to_async
def _fix_database():
    """Ensure BotSettings table is correctly set up - synchronous version"""
    logger.info("Checking database structure - sync version")
    token = get_bot_token()
    
    try:
        # Check if the table exists
        with connection.cursor() as cursor:
            cursor.execute("""
                SELECT EXISTS (
                    SELECT FROM information_schema.tables 
                    WHERE table_name='admin_panel_botsettings'
                ) AS table_exists
            """)
            table_exists = cursor.fetchone()[0]
            
            if not table_exists:
                logger.info("BotSettings table doesn't exist, creating it")
                cursor.execute("""
                    CREATE TABLE admin_panel_botsettings (
                        id SERIAL PRIMARY KEY,
                        bot_token VARCHAR(255) NOT NULL,
                        bot_username VARCHAR(255) NULL,
                        welcome_message TEXT NULL,
                        auth_guide_text TEXT NULL,
                        menu_style VARCHAR(50) NULL
                    )
                """)
            
            # Check columns
            cursor.execute("""
                SELECT column_name FROM information_schema.columns 
                WHERE table_name='admin_panel_botsettings'
            """)
            columns = [row[0] for row in cursor.fetchall()]
            logger.info(f"BotSettings columns: {columns}")
            
            # Add missing columns
            if 'bot_username' not in columns:
                logger.info("Adding missing bot_username column")
                cursor.execute('ALTER TABLE admin_panel_botsettings ADD COLUMN bot_username VARCHAR(255) NULL')
            
            if 'welcome_message' not in columns:
                logger.info("Adding missing welcome_message column")
                cursor.execute('ALTER TABLE admin_panel_botsettings ADD COLUMN welcome_message TEXT NULL')
            
            if 'auth_guide_text' not in columns:
                logger.info("Adding missing auth_guide_text column")
                cursor.execute('ALTER TABLE admin_panel_botsettings ADD COLUMN auth_guide_text TEXT NULL')
            
            if 'menu_style' not in columns:
                logger.info("Adding missing menu_style column")
                cursor.execute('ALTER TABLE admin_panel_botsettings ADD COLUMN menu_style VARCHAR(50) NULL')
            
            # Check if settings exist
            cursor.execute('SELECT COUNT(*) FROM admin_panel_botsettings')
            count = cursor.fetchone()[0]
            
            if count == 0:
                logger.info("No settings found, inserting default settings")
                cursor.execute("""
                    INSERT INTO admin_panel_botsettings 
                    (bot_token, bot_username, menu_style)
                    VALUES (%s, %s, %s)
                """, [token, 'Channels_hunt_bot', 'default'])
            else:
                logger.info("Updating existing settings")
                cursor.execute("""
                    UPDATE admin_panel_botsettings
                    SET bot_token = %s, bot_username = %s
                    WHERE id = (SELECT MIN(id) FROM admin_panel_botsettings)
                """, [token, 'Channels_hunt_bot'])
        
        connection.commit()
        logger.info("Database structure fixed successfully")
        return True
    except Exception as e:
        logger.error(f"Database fix failed: {e}")
        logger.error(traceback.format_exc())
        try:
            connection.rollback()
        except:
            pass
        return False

# Create an async wrapper around the database fix function
fix_database = sync_to_async(_fix_database)

def distribute_token(token):
    """Distribute token to all necessary locations"""
    logger.info("Distributing token to all locations")
    
    # 1. Update config.py
    try:
        config_path = os.path.join('tg_bot', 'config.py')
        if os.path.exists(config_path):
            with open(config_path, 'r') as f:
                lines = f.readlines()
            
            token_line_found = False
            with open(config_path, 'w') as f:
                for line in lines:
                    if line.strip().startswith('TOKEN_BOT'):
                        f.write(f'TOKEN_BOT = "{token}"\n')
                        token_line_found = True
                    else:
                        f.write(line)
                
                # Add token if not found
                if not token_line_found:
                    f.write(f'\n# Added by fix script\nTOKEN_BOT = "{token}"\n')
            
            logger.info("✅ Updated config.py")
    except Exception as e:
        logger.error(f"Failed to update config.py: {e}")
    
    # 2. Update bot_token.env
    try:
        with open('bot_token.env', 'w') as f:
            f.write(f'BOT_TOKEN={token}')
        logger.info("✅ Updated bot_token.env")
    except Exception as e:
        logger.error(f"Failed to update bot_token.env: {e}")
    
    # 3. Set environment variable
    os.environ['BOT_TOKEN'] = token
    logger.info("✅ Updated environment variable")

# Make this function synchronous so we can wrap it with sync_to_async
@sync_to_async
def update_botsettings_with_username(token, username):
    """Update BotSettings with username - sync version that's wrapped to be async-safe"""
    try:
        settings = BotSettings.objects.first()
        if settings:
            settings.bot_token = token
            settings.bot_username = username
            settings.save()
            logger.info(f"Updated BotSettings with username: {username}")
            return True
        return False
    except Exception as e:
        logger.error(f"Failed to update BotSettings with username: {e}")
        return False

async def main():
    """Main execution function"""
    logger.info("=== Starting bot connection fix ===")
    logger.info(f"Current time: {datetime.now()}")
    
    # Step 1: Get token
    token = get_bot_token()
    if not token:
        logger.error("Failed to get bot token")
        return False
    
    # Step 2: Distribute token
    distribute_token(token)
    
    # Step 3: Fix database - use sync_to_async
    try:
        db_fixed = await fix_database()
        if not db_fixed:
            logger.warning("Database fix encountered issues")
    except Exception as e:
        logger.error(f"Error in fix_database: {e}")
        db_fixed = False
    
    # Step 4: Verify token
    verified, bot_info = await verify_token(token)
    
    # Step 5: Restart bot if needed
    if verified:
        logger.info("Bot connection verified successfully!")
        
        # Add bot username to BotSettings if it was verified
        if bot_info:
            await update_botsettings_with_username(token, bot_info.username)
        
        return True
    else:
        logger.error("Bot verification failed")
        return False

if __name__ == "__main__":
    try:
        result = asyncio.run(main())
        if result:
            logger.info("=== Fix completed successfully ===")
            sys.exit(0)
        else:
            logger.error("=== Fix completed with errors ===")
            sys.exit(1)
    except KeyboardInterrupt:
        logger.info("Fix interrupted by user")
        sys.exit(2)
    except Exception as e:
        logger.error(f"Unhandled exception: {e}")
        logger.error(traceback.format_exc())
        sys.exit(3) 