import os
import asyncio
import logging
import argparse
from telethon import TelegramClient, errors
from tg_bot.config import API_ID, API_HASH
import sys
import traceback
from telethon.errors import SessionPasswordNeededError, FloodWaitError, PhoneCodeInvalidError
import django
from asgiref.sync import sync_to_async
import shutil
from asyncio import sleep
from django.conf import settings
from datetime import datetime

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

# Global variables to store code input state
_waiting_for_code = {}
_input_codes = {}

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

async def input_code(phone, code):
    """
    Function to input verification code from bot
    
    Args:
        phone: Phone number
        code: Verification code
        
    Returns:
        bool: Success or failure
    """
    if phone not in _waiting_for_code:
        logger.error(f"No authentication in progress for {phone}")
        return False
        
    _input_codes[phone] = code
    logger.info(f"Input code received for {phone}: {code}")
    
    # Wait for the code to be processed
    try:
        start_time = datetime.now()
        max_wait = 60  # seconds
        
        while phone in _waiting_for_code:
            await asyncio.sleep(1)
            elapsed = (datetime.now() - start_time).total_seconds()
            if elapsed > max_wait:
                logger.warning(f"Timeout waiting for code to be processed for {phone}")
                if phone in _waiting_for_code:
                    del _waiting_for_code[phone]
                if phone in _input_codes:
                    del _input_codes[phone]
                return False
                
        # If we got here, the code was processed
        return True
    except Exception as e:
        logger.error(f"Error in input_code: {e}")
        return False

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
    os.makedirs(os.path.join(settings.BASE_DIR, 'data', 'sessions'), exist_ok=True)
    
    logger.info(f"Creating new Telethon session for {phone}")
    
    # Initialize client
    client = TelegramClient(session_name, api_id, api_hash)
    
    try:
        await client.connect()
        
        # Check if already authenticated
        if await client.is_user_authorized():
            logger.info(f"Already authorized for session {session_name}")
            await client.disconnect()
            
            # Create or update database record using sync_to_async
            await _update_session_in_db(phone, api_id, api_hash, session_name, False)
            
            return True
            
        # Start authorization
        _waiting_for_code[phone] = True
        
        # Create or update database record
        await _update_session_in_db(phone, api_id, api_hash, None, True)
        
        try:
            # Send code request
            code_sent = await client.send_code_request(phone)
            logger.info(f"Code sent to {phone}")
            
            # Wait for code input
            code = None
            timeout = 300  # 5 minutes
            start_time = datetime.now()
            
            while True:
                # Check if code was provided via bot
                if phone in _input_codes:
                    code = _input_codes[phone]
                    del _input_codes[phone]
                    break
                    
                # Check timeout
                elapsed = (datetime.now() - start_time).total_seconds()
                if elapsed > timeout:
                    logger.warning(f"Timeout waiting for code input for {phone}")
                    if phone in _waiting_for_code:
                        del _waiting_for_code[phone]
                    await client.disconnect()
                    return False
                    
                # Sleep before checking again
                await asyncio.sleep(1)
                
            # Sign in with code
            logger.info(f"Signing in with code for {phone}")
            try:
                await client.sign_in(phone, code)
            except SessionPasswordNeededError:
                # 2FA password required
                logger.warning(f"2FA password required for {phone}")
                # TODO: Handle 2FA via bot
                await client.disconnect()
                return False
            except PhoneCodeInvalidError:
                logger.error(f"Invalid code for {phone}")
                await client.disconnect()
                return False
                
        except errors.FloodWaitError as e:
            # Handle rate limiting
            hours, remainder = divmod(e.seconds, 3600)
            minutes, seconds = divmod(remainder, 60)
            time_str = f"{hours}h {minutes}m {seconds}s" if hours > 0 else f"{minutes}m {seconds}s"
            
            logger.warning(f"FloodWaitError: Need to wait {time_str}")
            
            # Create a database record anyway so the admin knows
            await _update_session_in_db(phone, api_id, api_hash, None, True)
            
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
        
        # Update database record with authenticated status
        await _update_session_in_db(phone, api_id, api_hash, session_name, False)
        
        # Copy session file to data/sessions
        dest_path = os.path.join(settings.BASE_DIR, 'data', 'sessions', f"{session_name}.session")
        src_path = f"{session_name}.session"
        
        if os.path.exists(src_path):
            shutil.copy2(src_path, dest_path)
            logger.info(f"Session file copied to {dest_path}")
        
        logger.info(f"Session creation completed successfully for {phone}")
        return True
        
    except Exception as e:
        logger.error(f"Error creating session for {phone}: {e}")
        logger.error(traceback.format_exc())
        return False
    finally:
        # Clean up
        if phone in _waiting_for_code:
            del _waiting_for_code[phone]
        try:
            await client.disconnect()
        except:
            pass

async def _update_session_in_db(phone, api_id, api_hash, session_file, needs_auth):
    """
    Update or create session record in database
    
    Args:
        phone: Phone number
        api_id: API ID
        api_hash: API Hash
        session_file: Path to session file
        needs_auth: Whether the session needs authentication
    """
    try:
        from admin_panel.models import TelegramSession
        
        # Use atomic operation to avoid issues with created_at field
        @sync_to_async
        def update_db():
            try:
                # Find existing session or create new one
                session, created = TelegramSession.objects.get_or_create(
                    phone=phone,
                    defaults={
                        'api_id': api_id,
                        'api_hash': api_hash,
                        'session_file': session_file,
                        'is_active': True,
                        'needs_auth': needs_auth
                    }
                )
                
                if not created:
                    # Update existing record safely
                    session.api_id = api_id
                    session.api_hash = api_hash
                    session.is_active = True
                    
                    # Use update_fields to avoid nullifying created_at
                    update_fields = ['api_id', 'api_hash', 'is_active', 'updated_at']
                    
                    # Only update session_file if it has changed
                    if session_file is not None and session.session_file != session_file:
                        session.session_file = session_file
                        update_fields.append('session_file')
                        
                    if hasattr(session, 'needs_auth'):
                        session.needs_auth = needs_auth
                        update_fields.append('needs_auth')
                        
                    session.save(update_fields=update_fields)
                    
                logger.info(f"{'Created' if created else 'Updated'} session record in database for {phone} with needs_auth={needs_auth} (ID: {session.id})")
                return session.id
                
            except Exception as e:
                logger.error(f"Error updating database: {e}")
                logger.error(traceback.format_exc())
                return None
                
        return await update_db()
            
    except Exception as e:
        logger.error(f"Error in _update_session_in_db: {e}")
        logger.error(traceback.format_exc())
        return None

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


