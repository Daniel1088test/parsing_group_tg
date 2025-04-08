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
import time

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
_waiting_for_password = {}
_input_passwords = {}
_clients = {}

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
        max_wait = 120  # seconds
        
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
        # Check if 2FA is required
        if phone in _waiting_for_password:
            logger.info(f"2FA required for {phone}")
            return "2FA_REQUIRED"
        
        return True
    except Exception as e:
        logger.error(f"Error in input_code: {e}")
        return False

async def input_password(phone, password):
    """
    Function to input 2FA password from bot
    
    Args:
        phone: Phone number
        password: 2FA password
        
    Returns:
        bool: Success or failure
    """
    if phone not in _waiting_for_password:
        logger.error(f"No 2FA authentication in progress for {phone}")
        return False
        
    _input_passwords[phone] = password
    logger.info(f"Input password received for {phone}")
    
    # Wait for the password to be processed
    try:
        start_time = datetime.now()
        max_wait = 60  # seconds
        
        while phone in _waiting_for_password:
            await asyncio.sleep(1)
            elapsed = (datetime.now() - start_time).total_seconds()
            if elapsed > max_wait:
                logger.warning(f"Timeout waiting for password to be processed for {phone}")
                if phone in _waiting_for_password:
                    del _waiting_for_password[phone]
                if phone in _input_passwords:
                    del _input_passwords[phone]
                return False
                
        # If we got here, the password was processed
        return True
    except Exception as e:
        logger.error(f"Error in input_password: {e}")
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
    _clients[phone] = client
    
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
                # Code accepted and no 2FA required
                if phone in _waiting_for_code:
                    del _waiting_for_code[phone]
            except SessionPasswordNeededError:
                # 2FA password required
                logger.warning(f"2FA password required for {phone}")
                
                # Mark that we need a 2FA password
                _waiting_for_password[phone] = True
                if phone in _waiting_for_code:
                    del _waiting_for_code[phone]
                
                # Wait for password input
                password = None
                timeout = 300  # 5 minutes
                start_time = datetime.now()
                
                while True:
                    # Check if password was provided via bot
                    if phone in _input_passwords:
                        password = _input_passwords[phone]
                        del _input_passwords[phone]
                        break
                        
                    # Check timeout
                    elapsed = (datetime.now() - start_time).total_seconds()
                    if elapsed > timeout:
                        logger.warning(f"Timeout waiting for 2FA password input for {phone}")
                        if phone in _waiting_for_password:
                            del _waiting_for_password[phone]
                        await client.disconnect()
                        return False
                        
                    # Sleep before checking again
                    await asyncio.sleep(1)
                
                # Sign in with 2FA password
                try:
                    await client.sign_in(password=password)
                    # Password accepted
                    if phone in _waiting_for_password:
                        del _waiting_for_password[phone]
                except Exception as e:
                    logger.error(f"Error with 2FA password for {phone}: {e}")
                    if phone in _waiting_for_password:
                        del _waiting_for_password[phone]
                    await client.disconnect()
                    return False
                
            except PhoneCodeInvalidError:
                logger.error(f"Invalid code for {phone}")
                if phone in _waiting_for_code:
                    del _waiting_for_code[phone]
                await client.disconnect()
                return False
                
        except FloodWaitError as e:
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
        if phone in _waiting_for_password:
            del _waiting_for_password[phone]
        try:
            await client.disconnect()
        except:
            pass
        if phone in _clients:
            del _clients[phone]

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
                        'needs_auth': needs_auth,
                        # Add an auth token if this is a new session that needs authentication
                        'auth_token': f"auth_{int(time.time())}" if needs_auth and not session_file else None
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
                    
                    # Update auth_token if needed
                    if needs_auth and not session.auth_token:
                        session.auth_token = f"auth_{session.id}_{int(time.time())}"
                        update_fields.append('auth_token')
                    
                    # Encode and store the session data if file exists
                    if session_file and not needs_auth:
                        try:
                            session_path = f"{session_file}.session"
                            if os.path.exists(session_path):
                                with open(session_path, 'rb') as f:
                                    session_data = f.read()
                                    # Base64 encode the session data for storage
                                    import base64
                                    encoded_data = base64.b64encode(session_data).decode('utf-8')
                                    session.session_data = encoded_data
                                    update_fields.append('session_data')
                                    logger.info(f"Encoded session data for {phone} ({len(encoded_data)} bytes)")
                        except Exception as e:
                            logger.error(f"Error encoding session file: {e}")
                        
                    session.save(update_fields=update_fields)
                    
                # If this is a newly created session, try to encode the session data
                elif session_file and not needs_auth:
                    try:
                        session_path = f"{session_file}.session"
                        if os.path.exists(session_path):
                            with open(session_path, 'rb') as f:
                                session_data = f.read()
                                # Base64 encode the session data for storage
                                import base64
                                encoded_data = base64.b64encode(session_data).decode('utf-8')
                                session.session_data = encoded_data
                                session.save(update_fields=['session_data'])
                                logger.info(f"Encoded session data for new session {phone} ({len(encoded_data)} bytes)")
                    except Exception as e:
                        logger.error(f"Error encoding session file for new session: {e}")
                    
                logger.info(f"{'Created' if created else 'Updated'} session record in database for {phone} with needs_auth={needs_auth} (ID: {session.id})")
                
                # If this session needs auth, provide instructions
                if needs_auth:
                    bot_username = "Channels_hunt_bot"  # Default bot username
                    try:
                        # Try to get from settings if possible
                        from django.conf import settings
                        if hasattr(settings, 'TELEGRAM_BOT_USERNAME'):
                            bot_username = settings.TELEGRAM_BOT_USERNAME
                    except:
                        pass
                        
                    auth_token = session.auth_token or f"auth_{session.id}_{int(time.time())}"
                    logger.info(f"\n======== AUTHENTICATION REQUIRED ========\n"
                               f"Session {session.id} ({phone}) needs authentication.\n"
                               f"Please use one of these methods:\n"
                               f"1. Send /authorize command to @{bot_username} on Telegram\n"
                               f"2. Click 'Authorize' button on the Sessions page in web interface\n"
                               f"3. Use this deep link: https://t.me/{bot_username}?start={auth_token}\n"
                               f"=========================================\n")
                
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

async def restore_session_from_db(session_id_or_phone):
    """
    Restore a session file from the database encoded data
    
    Args:
        session_id_or_phone: Session ID or phone number
        
    Returns:
        tuple: (bool success, str session_path or None)
    """
    try:
        from admin_panel.models import TelegramSession
        
        @sync_to_async
        def get_session():
            try:
                # Try to get by ID first
                try:
                    session_id = int(session_id_or_phone)
                    return TelegramSession.objects.get(id=session_id)
                except (ValueError, TelegramSession.DoesNotExist):
                    # Try by phone instead
                    return TelegramSession.objects.get(phone=session_id_or_phone)
            except Exception:
                return None
                
        session = await get_session()
        if not session:
            logger.warning(f"Session not found: {session_id_or_phone}")
            return False, None
            
        # Check if we have encoded session data
        if not session.session_data:
            logger.warning(f"No encoded session data for {session_id_or_phone}")
            return False, None
            
        try:
            # Decode the session data
            import base64
            decoded_data = base64.b64decode(session.session_data)
            
            # Determine session file path
            if session.session_file:
                session_path = session.session_file
            else:
                session_path = f"telethon_session_{session.phone.replace('+', '')}"
                
            # Create parent directories if needed
            os.makedirs('data/sessions', exist_ok=True)
            
            # Always write to both locations for redundancy
            paths = [
                f"{session_path}.session",
                f"data/sessions/{session_path}.session"
            ]
            
            for path in paths:
                with open(path, 'wb') as f:
                    f.write(decoded_data)
                logger.info(f"Restored session file to {path}")
                
            # Update the session in DB to make sure it's marked as not needing auth
            if hasattr(session, 'needs_auth') and session.needs_auth:
                @sync_to_async
                def update_session():
                    session.needs_auth = False
                    session.save(update_fields=['needs_auth'])
                    
                await update_session()
                logger.info(f"Updated session {session_id_or_phone} as authenticated")
                
            return True, session_path
            
        except Exception as e:
            logger.error(f"Error restoring session from database: {e}")
            logger.error(traceback.format_exc())
            return False, None
            
    except Exception as e:
        logger.error(f"Error in restore_session_from_db: {e}")
        logger.error(traceback.format_exc())
        return False, None

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


