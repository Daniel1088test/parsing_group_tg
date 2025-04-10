"""
Script to automatically create a basic Telethon session file without user interaction.
This is useful for automated deployments where user interaction is not possible.

Usage:
    python -m tg_bot.create_session

The script will create 'telethon_session.session' file that can be used by the application.
"""

import os
import asyncio
import logging
import sys
from telethon import TelegramClient, sessions

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S',
)
logger = logging.getLogger('create_session')

# Hardcoded values - no need to import from config.py
API_ID = 19840544
API_HASH = "c839f28bad345082329ec086fca021fa"

async def create_session_file():
    """Create a basic Telethon session file"""
    logger.info("Creating basic Telethon session file")
    
    # Define session files to create
    session_files = ['telethon_session', 'telethon_user_session', 'anon']
    
    # Check if any session files already exist
    existing_files = [f"{file}.session" for file in session_files if os.path.exists(f"{file}.session")]
    if existing_files:
        logger.info(f"Found existing session files: {', '.join(existing_files)}")
        logger.info("Using the first existing session file as the base")
        return True
    
    try:
        # Create a basic session that doesn't require authorization
        # This won't be fully functional for user operations but will allow the 
        # application to start without errors
        main_file = 'telethon_session'
        logger.info(f"Creating session file: {main_file}.session")
        
        # Create a client with integer API_ID 
        client = TelegramClient(main_file, API_ID, API_HASH)
        
        # Just connect without attempting to sign in
        await client.connect()
        logger.info("Successfully connected to Telegram API")
        
        # Save the session
        await client.disconnect()
        logger.info(f"Created session file: {main_file}.session")
        
        # Create copies for alternative session names
        if os.path.exists(f"{main_file}.session"):
            for alt_name in [f for f in session_files if f != main_file]:
                try:
                    import shutil
                    shutil.copy2(f"{main_file}.session", f"{alt_name}.session")
                    logger.info(f"Created copy of session file as {alt_name}.session")
                except Exception as e:
                    logger.error(f"Error creating copy for {alt_name}: {e}")
        
        logger.info("Session files created successfully")
        return True
    except Exception as e:
        logger.error(f"Error creating session file: {e}")
        import traceback
        logger.error(f"Traceback: {traceback.format_exc()}")
        return False

if __name__ == "__main__":
    logger.info("=== Automatic Telethon Session Creation ===")
    logger.info(f"Using API ID: {API_ID}")
    logger.info("This will create basic session files for Telethon")
    
    try:
        success = asyncio.run(create_session_file())
        
        if success:
            logger.info("\n=== Session Creation Successful ===")
            logger.info("Basic session files have been created")
            logger.info("Note: These files allow the application to start, but for full functionality")
            logger.info("you should still run the proper authorization: python -m tg_bot.auth_telethon")
        else:
            logger.error("\n=== Session Creation Failed ===")
            logger.error("Please check your internet connection and Telegram API credentials.")
            sys.exit(1)
    except KeyboardInterrupt:
        logger.info("\nSession creation cancelled by user.")
        sys.exit(1)
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        import traceback
        logger.error(f"Traceback: {traceback.format_exc()}")
        sys.exit(1) 