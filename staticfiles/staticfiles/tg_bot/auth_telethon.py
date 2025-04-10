import os
import asyncio
import logging
import argparse
from telethon import TelegramClient, errors
from tg_bot.config import API_ID, API_HASH

# Add the TelethonClient class
class TelethonClient(TelegramClient):
    """
    Custom Telethon client class that extends the base TelegramClient
    to provide additional functionality specific to our application.
    """
    def __init__(self, session, api_id=None, api_hash=None):
        """
        Initialize the client with the provided session information.
        
        Args:
            session: Session string or file path
            api_id: Telegram API ID (defaults to config value if None)
            api_hash: Telegram API hash (defaults to config value if None)
        """
        # Use provided values or fall back to config
        api_id = api_id or API_ID
        api_hash = api_hash or API_HASH
        
        super().__init__(session, api_id, api_hash)
        
        self.logger = logging.getLogger('telethon_client')
        self.logger.info(f"Initialized TelethonClient with session: {session}")

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S',
)
logger = logging.getLogger('telethon_auth')

async def authorize_telethon(delete_existing=False):
    """
    Authorize Telethon by creating a new session or using an existing one.
    This function needs to be run interactively to handle phone number input and verification code.
    IMPORTANT: You must use a regular user account, NOT a bot account!
    
    Args:
        delete_existing: If True, delete existing session file if it exists
    """
    logger.info("Starting Telethon authorization process...")
    logger.info(f"API ID: {API_ID}")
    logger.info(f"API HASH: {API_HASH[:4]}...{API_HASH[-4:]}")  # Show only first and last 4 characters for security
    
    # Use a different session file name to avoid conflicts with bot
    session_file = 'telethon_user_session'
    
    # Check if session file exists and delete if requested
    if os.path.exists(f'{session_file}.session'):
        if delete_existing:
            try:
                os.remove(f'{session_file}.session')
                logger.info(f"Existing session file '{session_file}.session' deleted.")
            except Exception as e:
                logger.error(f"Error deleting session file: {e}")
                return False
        else:
            logger.info(f"Session file '{session_file}.session' already exists.")
    
    client = TelegramClient(session_file, API_ID, API_HASH)
    
    try:
        await client.connect()
        
        if await client.is_user_authorized():
            logger.info("Already authorized! Session file exists and is valid.")
            me = await client.get_me()
            logger.info(f"Authorized as: {me.first_name} (@{me.username}) [ID: {me.id}]")
        else:
            logger.info("Authorization required. Please follow the prompts:")
            logger.info("IMPORTANT: You must use a regular user account phone number, NOT a bot!")
            
            try:
                # Start the client which will prompt for phone number and code
                await client.start()
                
                me = await client.get_me()
                logger.info(f"Successfully authorized as: {me.first_name} (@{me.username}) [ID: {me.id}]")
            except errors.FloodWaitError as e:
                # Calculate time in more human-readable format
                hours, remainder = divmod(e.seconds, 3600)
                minutes, seconds = divmod(remainder, 60)
                
                time_str = ""
                if hours > 0:
                    time_str += f"{hours} hours "
                if minutes > 0:
                    time_str += f"{minutes} minutes "
                if seconds > 0 or (hours == 0 and minutes == 0):
                    time_str += f"{seconds} seconds"
                
                logger.error(f"Too many auth attempts! Telegram requires waiting {time_str} before trying again.")
                logger.error("Try again later or use a different phone number.")
                return False
        
        logger.info("Telethon authorization completed successfully!")
    except Exception as e:
        logger.error(f"Error during authorization: {e}")
        return False
    finally:
        await client.disconnect()
    
    return True

if __name__ == "__main__":
    # Parse command line arguments
    parser = argparse.ArgumentParser(description='Authorize Telethon client')
    parser.add_argument('--delete', action='store_true', help='Delete existing session file before authorization')
    args = parser.parse_args()
    
    # This script should be run directly: python -m tg_bot.auth_telethon
    try:
        print("=== Telethon Authorization Process ===")
        print(f"This will create or update your session file for API ID: {API_ID}")
        print("IMPORTANT: You must use a regular user account, NOT a bot!")
        print("You'll need your phone number and may need to enter a verification code.")
        
        if args.delete:
            print("WARNING: The --delete flag is set. Any existing session file will be deleted.")
            
        print("Press Ctrl+C at any time to cancel.\n")
        
        success = asyncio.run(authorize_telethon(args.delete))
        
        if success:
            print("\n=== Authorization Successful ===")
            print("You can now run the main application.")
        else:
            print("\n=== Authorization Failed ===")
            print("Please check your internet connection and Telegram API credentials.")
    except KeyboardInterrupt:
        print("\nAuthorization process cancelled by user.")


