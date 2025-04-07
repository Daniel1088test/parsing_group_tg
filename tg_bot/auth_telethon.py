import os
import asyncio
import logging
import argparse
import sys
import getpass
from telethon import TelegramClient, errors

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S',
)
logger = logging.getLogger('telethon_auth')

# Check if we're on Windows to handle SSL issues
ON_WINDOWS = sys.platform.startswith('win')

# Hardcoded values - don't rely on config.py loading correctly
API_ID = 19840544  # Integer
API_HASH = "c839f28bad345082329ec086fca021fa"  # String

async def interactive_auth(client):
    """Interactively authorize the client with user input for phone and code"""
    try:
        logger.info("Starting interactive authorization...")
        logger.info("IMPORTANT: You must use a regular user account phone number, NOT a bot!")
        
        # Ask for phone number
        phone = input("Please enter your phone number (include country code, e.g. +380xxxxxxxxx): ")
        
        # Request code
        await client.send_code_request(phone)
        logger.info(f"Code sent to {phone}. Please check your Telegram app or SMS.")
        
        # Get verification code
        code = input("Enter the code you received: ")
        
        try:
            await client.sign_in(phone, code)
            me = await client.get_me()
            logger.info(f"Successfully authorized as {me.first_name} (@{me.username}) [ID: {me.id}]")
            return True
        except errors.SessionPasswordNeededError:
            # Two-factor authentication is enabled
            logger.info("Two-factor authentication is enabled.")
            password = getpass.getpass("Please enter your 2FA password: ")
            await client.sign_in(password=password)
            me = await client.get_me()
            logger.info(f"Successfully authorized with 2FA as {me.first_name} (@{me.username}) [ID: {me.id}]")
            return True
        
    except errors.PhoneCodeInvalidError:
        logger.error("Invalid code provided. Please try again.")
        return False
    except errors.PhoneCodeExpiredError:
        logger.error("Code expired. Please restart the authorization process.")
        return False
    except errors.FloodWaitError as e:
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
        return False
    except Exception as e:
        logger.error(f"Error during authorization: {e}")
        return False

async def authorize_telethon(delete_existing=False, force_auth=False):
    """
    Authorize Telethon by creating a new session or using an existing one.
    This function needs to be run interactively to handle phone number input and verification code.
    IMPORTANT: You must use a regular user account, NOT a bot account!
    
    Args:
        delete_existing: If True, delete existing session file if it exists
        force_auth: If True, force interactive authorization even if session exists
    """
    logger.info("Starting Telethon authorization process...")
    logger.info(f"API ID: {API_ID}")
    logger.info(f"API HASH: {API_HASH[:4]}...{API_HASH[-4:]}")  # Show only first and last 4 characters for security
    
    # Use a different session file name to avoid conflicts with bot
    session_file = 'telethon_user_session'
    
    # Check for existing session files and handle accordingly
    session_files = []
    for file in ['telethon_user_session.session', 'telethon_session.session', 'anon.session']:
        if os.path.exists(file):
            session_files.append(file)
    
    if session_files:
        if delete_existing:
            for file in session_files:
                try:
                    os.remove(file)
                    logger.info(f"Deleted existing session file: {file}")
                except Exception as e:
                    logger.error(f"Failed to delete session file {file}: {e}")
        else:
            logger.info(f"Found existing session files: {', '.join(session_files)}")
            # Use the first found session file
            session_file = session_files[0].replace('.session', '')
            logger.info(f"Using existing session file: {session_file}")

    # Create copy of session file to avoid concurrency issues
    client = None
    try:
        # Create client with custom connection settings
        connection_params = {}
        if ON_WINDOWS:
            # On Windows, we need special connection settings to avoid SSL issues
            from telethon.network import connection
            connection_params = {
                'connection': connection.ConnectionTcpFull,
                'auto_reconnect': True,
                'retry_delay': 1,
                'connection_retries': 3,
            }
        
        # Initialize the client
        logger.info(f"Creating Telethon client with session file: {session_file}")
        client = TelegramClient(session_file, API_ID, API_HASH, **connection_params)
        
        # Connect with error handling for SSL issues
        try:
            await client.connect()
            logger.info("Successfully connected to Telegram")
        except ImportError as e:
            if "libssl" in str(e) or "ssl" in str(e):
                logger.warning("SSL library issues detected. Falling back to slower Python encryption.")
                logger.warning("For better performance, please install libssl or cryptg package.")
            else:
                raise
        
        # Check authorization and handle accordingly
        is_authorized = await client.is_user_authorized()
        if is_authorized and not force_auth:
            logger.info("Already authorized! Session file exists and is valid.")
            me = await client.get_me()
            logger.info(f"Authorized as: {me.first_name} (@{me.username}) [ID: {me.id}]")
            
            # Save a backup of the session file
            if os.path.exists(f'{session_file}.session'):
                backup_file = f'{session_file}_backup.session'
                try:
                    import shutil
                    shutil.copy2(f'{session_file}.session', backup_file)
                    logger.info(f"Created backup of session file: {backup_file}")
                except Exception as e:
                    logger.error(f"Failed to create backup of session file: {e}")
                    
            # Create copies for other session names for compatibility
            try:
                main_file = f'{session_file}.session'
                for alt_name in ['telethon_session.session', 'anon.session']:
                    if not os.path.exists(alt_name) and alt_name != main_file:
                        import shutil
                        shutil.copy2(main_file, alt_name)
                        logger.info(f"Created copy of session file as {alt_name} for compatibility")
            except Exception as e:
                logger.error(f"Error creating alternative session files: {e}")
        else:
            # Either not authorized or force_auth is True
            if not is_authorized:
                logger.info("Not authorized or authorization has expired. Starting interactive login...")
            else:
                logger.info("Forcing re-authorization as requested...")
                
            # Interactive authorization
            auth_success = await interactive_auth(client)
            
            if auth_success:
                # Create copies for other session names for compatibility
                try:
                    main_file = f'{session_file}.session'
                    for alt_name in ['telethon_session.session', 'anon.session']:
                        if not os.path.exists(alt_name) or alt_name != main_file:
                            import shutil
                            shutil.copy2(main_file, alt_name)
                            logger.info(f"Created copy of session file as {alt_name} for compatibility")
                except Exception as e:
                    logger.error(f"Error creating alternative session files: {e}")
            else:
                logger.error("Authorization failed. Please try again later.")
                return False
        
        logger.info("Telethon authorization completed successfully!")
        return True
    except Exception as e:
        logger.error(f"Error during authorization: {e}")
        import traceback
        logger.error(f"Traceback: {traceback.format_exc()}")
        return False
    finally:
        if client:
            try:
                await client.disconnect()
                logger.info("Telethon client disconnected")
            except:
                pass

if __name__ == "__main__":
    # Parse command line arguments
    parser = argparse.ArgumentParser(description='Authorize Telethon client')
    parser.add_argument('--delete', action='store_true', help='Delete existing session file before authorization')
    parser.add_argument('--force', action='store_true', help='Force interactive authorization even if session exists')
    args = parser.parse_args()
    
    # This script should be run directly: python -m tg_bot.auth_telethon
    try:
        print("=== Telethon Authorization Process ===")
        print(f"This will create or update your session file for API ID: {API_ID}")
        print("IMPORTANT: You must use a regular user account, NOT a bot!")
        print("You'll need your phone number and may need to enter a verification code.")
        
        if args.delete:
            print("WARNING: The --delete flag is set. Any existing session file will be deleted.")
        if args.force:
            print("WARNING: The --force flag is set. You will be asked to authorize even if a valid session exists.")
            
        print("Press Ctrl+C at any time to cancel.\n")
        
        success = asyncio.run(authorize_telethon(args.delete, args.force))
        
        if success:
            print("\n=== Authorization Successful ===")
            print("You can now run the main application.")
            print("✅ IMPORTANT: Your session is now fully authorized and should work correctly.")
        else:
            print("\n=== Authorization Failed ===")
            print("Please check your internet connection and Telegram API credentials.")
    except KeyboardInterrupt:
        print("\nAuthorization process cancelled by user.")


