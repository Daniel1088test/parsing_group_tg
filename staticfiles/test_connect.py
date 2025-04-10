"""
Simple test script to verify Telethon connectivity
"""

import os
import asyncio
import logging
from telethon import TelegramClient

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
)
logger = logging.getLogger('test_connect')

# Hardcoded API credentials
API_ID = 19840544
API_HASH = "c839f28bad345082329ec086fca021fa"

async def main():
    """Test Telethon connectivity"""
    logger.info("Creating Telethon client...")
    
    # Create session
    client = TelegramClient('test_connection', API_ID, API_HASH)
    
    try:
        logger.info("Connecting to Telegram...")
        await client.connect()
        
        if await client.is_user_authorized():
            me = await client.get_me()
            logger.info(f"Connected and authorized as: {me.first_name} (@{me.username})")
        else:
            logger.info("Connected but not authorized (this is expected for testing)")
        
        # Just as a test, try to get some dialogs
        try:
            dialogs = await client.get_dialogs(limit=5)
            logger.info(f"Successfully got {len(dialogs)} dialogs")
            
            # If we have dialogs, create a session file for the main app
            if dialogs:
                # Try to create basic session files that the app needs
                for session_name in ['telethon_session', 'telethon_user_session', 'anon']:
                    if not os.path.exists(f"{session_name}.session"):
                        # We can copy our test session file
                        import shutil
                        shutil.copy2("test_connection.session", f"{session_name}.session")
                        logger.info(f"Created session file: {session_name}.session")
                
                logger.info("Created necessary session files. The app should work now.")
        except Exception as e:
            logger.error(f"Error getting dialogs: {e}")
        
        logger.info("Test completed successfully!")
    except Exception as e:
        logger.error(f"Error connecting to Telegram: {e}")
    finally:
        # Disconnect
        await client.disconnect()
        logger.info("Disconnected from Telegram")
        
        # Clean up test session
        if os.path.exists('test_connection.session'):
            os.remove('test_connection.session')
            logger.info("Removed test session file")

if __name__ == "__main__":
    asyncio.run(main()) 