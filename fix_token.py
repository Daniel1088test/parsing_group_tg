#!/usr/bin/env python3
"""
Script to fix the Telegram bot token.
Run this script to set and validate a new token.
"""

import os
import sys
import django
import logging
import argparse

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger('token_fixer')

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
try:
    django.setup()
    logger.info("Django setup successful")
except Exception as e:
    logger.error(f"Django setup error: {e}")
    sys.exit(1)

def check_token(token):
    """Verify a token by connecting to the Telegram API"""
    try:
        import asyncio
        from aiogram import Bot
        
        async def verify_token():
            try:
                bot = Bot(token=token)
                me = await bot.get_me()
                await bot.session.close()
                return True, me.username
            except Exception as e:
                logger.error(f"Token verification failed: {e}")
                return False, str(e)
            
        # Run the verification
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            valid, username = loop.run_until_complete(verify_token())
            return valid, username
        finally:
            loop.close()
    except Exception as e:
        logger.error(f"Error during token verification: {e}")
        return False, str(e)

def update_bot_token(token):
    """Update the bot token in all possible locations"""
    try:
        # Update in environment variable
        os.environ['BOT_TOKEN'] = token
        
        # Update in database
        try:
            from admin_panel.models import BotSettings
            bot_settings = BotSettings.objects.first()
            if bot_settings:
                bot_settings.bot_token = token
                bot_settings.save()
                logger.info("Updated token in database")
            else:
                # Create new settings object if it doesn't exist
                BotSettings.objects.create(bot_token=token)
                logger.info("Created new settings with token in database")
        except Exception as db_error:
            logger.warning(f"Could not update token in database: {db_error}")
        
        # Create bot_token.env file for shell scripts
        with open('bot_token.env', 'w') as f:
            f.write(f"BOT_TOKEN={token}")
        logger.info("Created bot_token.env file")
        
        # Try to update config.py if it exists
        try:
            config_path = os.path.join('tg_bot', 'config.py')
            if os.path.exists(config_path):
                with open(config_path, 'r') as f:
                    lines = f.readlines()
                
                with open(config_path, 'w') as f:
                    for line in lines:
                        if line.startswith('TOKEN_BOT'):
                            f.write(f'TOKEN_BOT = "{token}"\n')
                        else:
                            f.write(line)
                logger.info("Updated token in config.py")
        except Exception as config_error:
            logger.warning(f"Could not update config.py: {config_error}")
            
        return True
    except Exception as e:
        logger.error(f"Error updating token: {e}")
        return False

def is_interactive():
    """Check if we're running in an interactive terminal"""
    # Is stdin a tty?
    if not sys.stdin.isatty():
        return False
    # Are we running in a CI/CD environment?
    if os.environ.get('CI') or os.environ.get('RAILWAY'):
        return False
    return True

def main():
    """Main function to set and verify the bot token"""
    # Check for command line arguments
    parser = argparse.ArgumentParser(description="Fix Telegram bot token")
    parser.add_argument('token', nargs='?', type=str, help="Telegram bot token to use")
    parser.add_argument('--skip-verify', action='store_true', help="Skip token verification")
    parser.add_argument('--non-interactive', action='store_true', help="Run in non-interactive mode")
    args = parser.parse_args()
    
    # Determine if we're in interactive mode
    interactive_mode = is_interactive() and not args.non_interactive
    
    # Get token from argument, positional arg, or prompt user
    token = args.token
    if not token and len(sys.argv) > 1 and sys.argv[1].startswith('5') and ':' in sys.argv[1]:
        # Token provided as first positional arg without --token flag
        token = sys.argv[1]
    
    if not token and interactive_mode:
        token = input("Enter your Telegram bot token: ")
    
    if not token:
        logger.error("No token provided. Use: python fix_token.py YOUR_TOKEN")
        return False
    
    # Verify token if not skipped and in interactive mode
    if not args.skip_verify and interactive_mode:
        logger.info("Verifying token...")
        valid, result = check_token(token)
        if valid:
            logger.info(f"✅ Token is valid! Connected to @{result}")
        else:
            logger.error(f"❌ Invalid token: {result}")
            if interactive_mode:
                retry = input("Token verification failed. Use it anyway? (y/n): ")
                if retry.lower() != 'y':
                    logger.info("Aborting token update")
                    return False
            else:
                logger.warning("Using token despite verification failure (non-interactive mode)")
    else:
        # In non-interactive mode or with skip-verify, we still try to verify for logging purposes
        # but don't stop if it fails
        if not args.skip_verify:
            logger.info("Verifying token in non-interactive mode...")
            valid, result = check_token(token)
            if valid:
                logger.info(f"✅ Token is valid! Connected to @{result}")
            else:
                logger.warning(f"⚠️ Token verification failed but continuing as requested: {result}")
    
    # Update token in all locations
    if update_bot_token(token):
        logger.info("Bot token updated successfully")
        
        if interactive_mode:
            print("\n==== NEXT STEPS ====")
            print("1. Restart your application with:")
            print("   python run.py")
            print("2. Or restart the Railway deployment")
            print("====================\n")
        
        return True
    else:
        logger.error("Failed to update bot token")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1) 