import os
import asyncio
import logging
import argparse
from telethon import TelegramClient, errors
from tg_bot.config import API_ID, API_HASH
import sys
import traceback
from telethon.errors import SessionPasswordNeededError
import django
from asgiref.sync import sync_to_async

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S',
)
logger = logging.getLogger('telethon_auth')

# Configure Django for model access
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()

from admin_panel.models import TelegramSession

async def verify_session(session_path, api_id=None, api_hash=None):
    """
    Verify if a session file is properly authorized
    
    Args:
        session_path: Path to the session file without .session extension
        api_id: Telegram API ID
        api_hash: Telegram API Hash
        
    Returns:
        tuple: (bool is_authorized, dict user_info or None)
    """
    if not api_id:
        api_id = API_ID
    if not api_hash:
        api_hash = API_HASH
        
    # Get just the filename without path or extension
    session_name = os.path.basename(session_path)
    if session_name.endswith('.session'):
        session_name = session_name[:-8]
        
    logger.info(f"Verifying session: {session_path}")
    
    if not os.path.exists(f"{session_path}.session"):
        logger.warning(f"Session file not found: {session_path}.session")
        return False, None
        
    client = TelegramClient(session_path, api_id, api_hash)
    
    try:
        await client.connect()
        
        if not await client.is_user_authorized():
            logger.warning(f"Session file exists but is not authorized: {session_path}")
            await client.disconnect()
            return False, None
            
        # Get user info
        me = await client.get_me()
        user_info = {
            'id': me.id,
            'first_name': me.first_name,
            'last_name': getattr(me, 'last_name', ''),
            'username': getattr(me, 'username', ''),
            'phone': getattr(me, 'phone', '')
        }
        
        logger.info(f"Session verified: {session_path} is authorized as @{user_info.get('username')}")
        await client.disconnect()
        return True, user_info
        
    except Exception as e:
        logger.error(f"Error verifying session {session_path}: {e}")
        logger.error(traceback.format_exc())
        try:
            await client.disconnect()
        except:
            pass
        return False, None

async def create_session_file(phone, api_id=None, api_hash=None, session_name=None, interactive=True):
    """
    Create a new Telethon session file with authorization
    
    Args:
        phone: Phone number with country code (e.g. +380667264351)
        api_id: Telegram API ID
        api_hash: Telegram API Hash
        session_name: Custom session name (default: telethon_session)
        interactive: Whether to ask for code interactively
        
    Returns:
        bool: Success or failure
    """
    if not api_id:
        api_id = API_ID
    if not api_hash:
        api_hash = API_HASH
    if not session_name:
        session_name = f'telethon_session_{phone.replace("+", "")}'
        
    # Create directories if they don't exist
    os.makedirs('data/sessions', exist_ok=True)
    
    # Session file paths
    main_session_path = f"{session_name}.session"
    session_copy_path = f"data/sessions/{session_name}.session"
    
    logger.info(f"Creating new Telethon session for {phone}")
    
    # In non-interactive mode, just create the database record but don't try to authenticate
    if not interactive:
        logger.info("Non-interactive mode: Cannot complete authorization. Record will be created in database.")
        
        # Create or update database record using sync_to_async
        try:
            @sync_to_async
            def update_session_in_db():
                try:
                    # First check if the session already exists
                    try:
                        session = TelegramSession.objects.get(phone=phone)
                        created = False
                    except TelegramSession.DoesNotExist:
                        # Create a new session
                        session = TelegramSession(
                            phone=phone,
                            api_id=api_id,
                            api_hash=api_hash,
                            is_active=True,
                            session_file=session_name,
                            needs_auth=True
                        )
                        created = True
                    
                    # Update existing or save new
                    if not created:
                        session.api_id = api_id
                        session.api_hash = api_hash
                        session.is_active = True
                        session.session_file = session_name
                        session.needs_auth = True
                    
                    session.save()
                    return created, session.id
                except Exception as e:
                    logger.error(f"Error in update_session_in_db: {e}")
                    return False, None
            
            created, session_id = await update_session_in_db()
            logger.info(f"{'Created' if created else 'Updated'} session record in database for {phone} with needs_auth=True (ID: {session_id})")
            return False
            
        except Exception as e:
            logger.error(f"Error updating database: {e}")
            logger.error(traceback.format_exc())
            return False
    
    client = TelegramClient(session_name, api_id, api_hash)
    
    try:
        await client.connect()
        
        if not await client.is_user_authorized():
            logger.info(f"Session not authorized. Starting authorization for {phone}")
            
            try:
                # Send authorization code request
                await client.send_code_request(phone)
                
                if interactive:
                    # Get verification code from user
                    auth_code = input(f'Enter the code you received for {phone}: ')
                    
                    try:
                        # Sign in with the code
                        await client.sign_in(phone, auth_code)
                    except SessionPasswordNeededError:
                        # If two-factor authentication is enabled
                        password = input("Two-factor authentication is enabled. Please enter your password: ")
                        await client.sign_in(password=password)
                else:
                    logger.error("Non-interactive mode: Cannot request verification code. Please run in interactive mode.")
                    
                    # Create or update database record with needs_auth=True
                    @sync_to_async
                    def update_session_in_db_after_flood():
                        try:
                            # First check if the session already exists
                            try:
                                session = TelegramSession.objects.get(phone=phone)
                                created = False
                            except TelegramSession.DoesNotExist:
                                # Create a new session
                                session = TelegramSession(
                                    phone=phone,
                                    api_id=api_id,
                                    api_hash=api_hash,
                                    is_active=True,
                                    session_file=session_name,
                                    needs_auth=True
                                )
                                created = True
                            
                            # Update existing or save new
                            if not created:
                                session.api_id = api_id
                                session.api_hash = api_hash
                                session.is_active = True
                                session.session_file = session_name
                                session.needs_auth = True
                            
                            session.save()
                            return created, session.id
                        except Exception as e:
                            logger.error(f"Error in update_session_in_db_after_flood: {e}")
                            return False, None
                    
                    created, session_id = await update_session_in_db_after_flood()
                    logger.info(f"{'Created' if created else 'Updated'} session record in database for {phone} with needs_auth=True (ID: {session_id})")
                    
                    await client.disconnect()
                    return False
            except errors.FloodWaitError as e:
                # Rate limited, handle gracefully
                wait_time = e.seconds
                hours, remainder = divmod(wait_time, 3600)
                minutes, seconds = divmod(remainder, 60)
                wait_msg = f"{hours}h {minutes}m {seconds}s" if hours > 0 else f"{minutes}m {seconds}s"
                
                logger.error(f"Rate limited: Need to wait {wait_msg} ({wait_time} seconds) for {phone}")
                
                # Create or update database record with needs_auth=True
                @sync_to_async
                def update_session_in_db_after_flood():
                    try:
                        # First check if the session already exists
                        try:
                            session = TelegramSession.objects.get(phone=phone)
                            created = False
                        except TelegramSession.DoesNotExist:
                            # Create a new session
                            session = TelegramSession(
                                phone=phone,
                                api_id=api_id,
                                api_hash=api_hash,
                                is_active=True,
                                session_file=session_name,
                                needs_auth=True
                            )
                            created = True
                        
                        # Update existing or save new
                        if not created:
                            session.api_id = api_id
                            session.api_hash = api_hash
                            session.is_active = True
                            session.session_file = session_name
                            session.needs_auth = True
                        
                        session.save()
                        return created, session.id
                    except Exception as e:
                        logger.error(f"Error in update_session_in_db_after_flood: {e}")
                        return False, None
                
                created, session_id = await update_session_in_db_after_flood()
                logger.info(f"{'Created' if created else 'Updated'} session record in database for {phone} with needs_auth=True (ID: {session_id})")
                
                await client.disconnect()
                return False
        
        # Get user information
        me = await client.get_me()
        if not me:
            logger.error(f"Failed to get user info after authorization")
            await client.disconnect()
            return False
            
        logger.info(f"Successfully authorized as: {me.first_name} (@{me.username or 'No username'}) [ID: {me.id}]")
        
        # Load dialogs for better channel handling
        logger.info("Loading dialogs...")
        await client.get_dialogs()
        logger.info("Dialogs loaded")
        
        # Create or update database record using sync_to_async
        try:
            @sync_to_async
            def update_session_in_db():
                try:
                    # First check if the session already exists
                    try:
                        session = TelegramSession.objects.get(phone=phone)
                        created = False
                    except TelegramSession.DoesNotExist:
                        # Create a new session
                        session = TelegramSession(
                            phone=phone,
                            api_id=api_id,
                            api_hash=api_hash,
                            is_active=True,
                            session_file=session_name,
                            needs_auth=False  # Session is now authorized
                        )
                        created = True
                    
                    # Update existing or save new
                    if not created:
                        session.api_id = api_id
                        session.api_hash = api_hash
                        session.is_active = True
                        session.session_file = session_name
                        session.needs_auth = False  # Session is now authorized
                    
                    session.save()
                    return created, session.id
                except Exception as e:
                    logger.error(f"Error in update_session_in_db: {e}")
                    return False, None
            
            created, session_id = await update_session_in_db()
            logger.info(f"{'Created' if created else 'Updated'} session record in database for {phone} with needs_auth=False (ID: {session_id})")
            
        except Exception as e:
            logger.error(f"Error updating database: {e}")
            logger.error(traceback.format_exc())
        
        # Close the connection
        await client.disconnect()
        
        # Copy session file to data/sessions directory
        if os.path.exists(main_session_path) and os.path.isfile(main_session_path):
            import shutil
            try:
                shutil.copy2(main_session_path, session_copy_path)
                logger.info(f"Session file copied to {session_copy_path}")
            except Exception as e:
                logger.error(f"Error copying session file: {e}")
        
        logger.info(f"Session creation completed successfully for {phone}")
        return True
    except Exception as e:
        logger.error(f"Error creating session for {phone}: {e}")
        logger.error(traceback.format_exc())
        return False
    finally:
        # Ensure client is disconnected
        try:
            if client and client.is_connected():
                await client.disconnect()
        except:
            pass

async def verify_all_sessions_in_db():
    """Verify all sessions in the database and update their status"""
    
    @sync_to_async
    def get_active_sessions():
        return list(TelegramSession.objects.filter(is_active=True))
    
    @sync_to_async
    def update_session(session, path):
        session.session_file = path
        session.needs_auth = False
        session.save()
        
    @sync_to_async
    def mark_session_needs_auth(session):
        session.needs_auth = True
        session.save()
    
    sessions = await get_active_sessions()
    logger.info(f"Verifying {len(sessions)} active sessions from database")
    
    results = []
    
    for session in sessions:
        # Define possible session paths
        session_name = session.session_file or f"telethon_session_{session.id}"
        possible_paths = [
            session_name,
            f"data/sessions/{session_name}",
            f"telethon_session_{session.id}",
            f"data/sessions/telethon_session_{session.id}",
            f"telethon_session_{session.phone.replace('+', '')}"
        ]
        
        # Try each path
        authorized = False
        user_info = None
        
        for path in possible_paths:
            if os.path.exists(f"{path}.session"):
                is_auth, info = await verify_session(path, session.api_id, session.api_hash)
                if is_auth:
                    authorized = True
                    user_info = info
                    await update_session(session, path)
                    break
        
        if not authorized:
            logger.warning(f"Session {session.id} ({session.phone}) is not properly authorized")
            await mark_session_needs_auth(session)
        else:
            logger.info(f"Session {session.id} ({session.phone}) is valid")
            
        results.append({
            'session_id': session.id,
            'phone': session.phone,
            'authorized': authorized,
            'user_info': user_info
        })
    
    return results

async def main():
    """Main function to run the script with command-line arguments"""
    parser = argparse.ArgumentParser(description='Telegram Session Creator and Verifier')
    parser.add_argument('--phone', type=str, help='Phone number with country code (e.g. +380667264351)')
    parser.add_argument('--verify', action='store_true', help='Verify all sessions in database')
    parser.add_argument('--verify-file', type=str, help='Verify a specific session file')
    args = parser.parse_args()
    
    print("\n=== Telethon Session Manager ===\n")
    
    if args.verify:
        results = await verify_all_sessions_in_db()
        print(f"\nVerified {len(results)} sessions:")
        for result in results:
            status = "✅ Authorized" if result['authorized'] else "❌ Not authorized"
            phone = result['phone']
            print(f"- Session ID {result['session_id']} ({phone}): {status}")
        return
    
    if args.verify_file:
        is_auth, user_info = await verify_session(args.verify_file)
        if is_auth:
            print(f"\n✅ Session {args.verify_file} is authorized")
            print(f"User: {user_info['first_name']} {user_info['last_name']} (@{user_info['username']})")
        else:
            print(f"\n❌ Session {args.verify_file} is NOT authorized")
        return
        
    # Create a new session
    phone = args.phone if args.phone else input("Enter phone number (with country code, e.g. +380123456789): ")
    
    success = await create_session_file(phone)
    
    if success:
        print("\n✅ Session created successfully!")
        print(f"The session file has been created and the session is registered in the database.")
        print(f"You can now use this session for parsing messages from Telegram channels.")
    else:
        print("\n❌ Failed to create session.")
        print("Please check the logs for more information.")

if __name__ == "__main__":
    asyncio.run(main())


