#!/usr/bin/env python3
"""
Script to verify and set the Telegram bot token.
Run this script before starting the bot to ensure the token is properly set.
"""

import os
import sys
import django
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger('token_setter')

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
try:
    django.setup()
    logger.info("Django setup successful")
except Exception as e:
    logger.error(f"Django setup error: {e}")
    sys.exit(1)

def get_and_set_bot_token():
    """Find and set the bot token from various sources"""
    # Check if the token is already set
    if 'BOT_TOKEN' in os.environ and os.environ['BOT_TOKEN']:
        logger.info("BOT_TOKEN already set in environment variables")
        return True
    
    # Try to get from Django settings
    try:
        from django.conf import settings
        if hasattr(settings, 'BOT_TOKEN') and settings.BOT_TOKEN:
            os.environ['BOT_TOKEN'] = settings.BOT_TOKEN
            logger.info("Set BOT_TOKEN from Django settings")
            return True
    except Exception as e:
        logger.warning(f"Failed to get token from Django settings: {e}")
    
    # Try to get from database
    try:
        from admin_panel.models import BotSettings
        bot_settings = BotSettings.objects.first()
        if bot_settings and bot_settings.bot_token:
            os.environ['BOT_TOKEN'] = bot_settings.bot_token
            logger.info("Set BOT_TOKEN from database")
            return True
    except Exception as e:
        logger.warning(f"Failed to get token from database: {e}")
    
    # Try to get from config.py
    try:
        sys.path.append(os.path.join(os.path.dirname(__file__), 'tg_bot'))
        try:
            from config import TOKEN_BOT
            if TOKEN_BOT:
                os.environ['BOT_TOKEN'] = TOKEN_BOT
                logger.info("Set BOT_TOKEN from config.py")
                return True
        except ImportError:
            # Create config.py if it doesn't exist
            config_dir = os.path.join(os.path.dirname(__file__), 'tg_bot')
            os.makedirs(config_dir, exist_ok=True)
            
            # Use a placeholder token that will be replaced later
            with open(os.path.join(config_dir, 'config.py'), 'w') as f:
                f.write('# Telegram Bot Configuration\n')
                f.write('TOKEN_BOT = "placeholder_token_fix_me"\n')
                f.write('ADMIN_ID = 123456789  # Change to your Telegram user ID\n')
                f.write('WEB_SERVER_HOST = "localhost"\n')
                f.write('WEB_SERVER_PORT = 8080\n')
            
            os.environ['BOT_TOKEN'] = "placeholder_token_fix_me"
            logger.info("Created config.py with placeholder token")
            return False
    except Exception as e:
        logger.warning(f"Failed to get/create token in config.py: {e}")
    
    # Use fallback token if all else fails
    fallback_token = "placeholder_token_replace_me"
    logger.warning(f"Using fallback token as last resort! Please set a proper token.")
    os.environ['BOT_TOKEN'] = fallback_token
    
    return False

if __name__ == "__main__":
    logger.info("Verifying and setting bot token...")
    success = get_and_set_bot_token()
    
    # Check the token by trying to connect to Telegram API
    try:
        import asyncio
        from aiogram import Bot
        
        async def check_token():
            try:
                bot = Bot(token=os.environ['BOT_TOKEN'])
                me = await bot.get_me()
                logger.info(f"✅ Bot token is valid. Connected to @{me.username}")
                await bot.session.close()
                return True
            except Exception as e:
                logger.error(f"❌ Bot token verification failed: {e}")
                return False
        
        # Run the async check
        token_valid = asyncio.run(check_token())
        
        if token_valid:
            # Export to a file for shell scripts
            with open('bot_token.env', 'w') as f:
                f.write(f"BOT_TOKEN={os.environ['BOT_TOKEN']}")
            logger.info("Saved token to bot_token.env file")
            
            # Print instructions
            print("\n=== TELEGRAM BOT TOKEN ===")
            print(f"Token: {os.environ['BOT_TOKEN']}")
            print("This token has been verified and is working correctly")
            print("===========================\n")
            sys.exit(0)
        else:
            logger.error("⚠️ The Telegram bot token is invalid!")
            print("\n=== BOT TOKEN ISSUE DETECTED ===")
            print("The Telegram bot token is invalid or has been revoked.")
            print("To fix this issue, you can:")
            print("1. Run: python fix_token.py")
            print("   This will help you set a new valid token.")
            print("2. Or set a valid token in one of these locations:")
            print("   - Environment variable BOT_TOKEN")
            print("   - tg_bot/config.py (TOKEN_BOT)")
            print("   - Database (BotSettings model)")
            print("===========================\n")
            
            # Write bot_token.env file anyway so the system can continue
            with open('bot_token.env', 'w') as f:
                f.write(f"BOT_TOKEN={os.environ['BOT_TOKEN']}")
            
            # Exiting with 0 to allow the application to continue
            # This is intentional since we want the app to run even with invalid token
            sys.exit(0)
            
    except Exception as e:
        logger.error(f"Error checking token: {e}")
        # Still exit with 0 to allow the application to continue
        sys.exit(0) 