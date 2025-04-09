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
        from config import TOKEN_BOT
        if TOKEN_BOT:
            os.environ['BOT_TOKEN'] = TOKEN_BOT
            logger.info("Set BOT_TOKEN from config.py")
            return True
    except Exception as e:
        logger.warning(f"Failed to get token from config.py: {e}")
    
    # Use fallback token if all else fails
    fallback_token = "7923260865:AAGWm7t0Zz2PqFPI5PldEVwrOC4HZ_5oP0c"
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
            logger.error("Please set a valid bot token in settings or environment variables")
            sys.exit(1)
            
    except Exception as e:
        logger.error(f"Error checking token: {e}")
        sys.exit(1) 