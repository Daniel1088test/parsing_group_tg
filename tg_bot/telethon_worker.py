import asyncio
import json
import os
import signal
import re
import logging
import traceback
from datetime import datetime
import django
from typing import Dict, Optional, Tuple

from telethon import TelegramClient, errors, client
from telethon.tl.functions.channels import JoinChannelRequest
from telethon.tl.types import MessageMediaPhoto, MessageMediaDocument, MessageMediaWebPage
from asgiref.sync import sync_to_async
from tg_bot.config import (
    API_ID, API_HASH, FILE_JSON, MAX_MESSAGES,
    CATEGORIES_JSON, DATA_FOLDER, MESSAGES_FOLDER
)

# configuration of logging
logging.basicConfig(    
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S',
)
logger = logging.getLogger('telegram_parser')

# config Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()

# import models and auth module
from admin_panel import models
from tg_bot.auth_telethon import verify_session, create_session_file

def _save_message_to_db(message_data):
    """
    save message to db
    """
    try:
        channel = models.Channel.objects.get(name=message_data['channel_name'])
        
        # Validate media file existence if media path is provided
        media_path = message_data.get('media', '')
        if media_path:
            from django.conf import settings
            import os
            
            # Check if the file exists
            full_path = os.path.join(settings.MEDIA_ROOT, media_path)
            if not os.path.exists(full_path):
                logger.warning(f"Media file not found: {full_path}")
                # Don't save non-existent media paths
                media_path = ""
        
        message = models.Message(
            text=message_data['text'],
            media=media_path,
            media_type=message_data['media_type'],
            telegram_message_id=message_data['message_id'],
            telegram_channel_id=message_data['channel_id'],
            telegram_link=message_data['link'],
            channel=channel,
            created_at=message_data['date'],
            session_used=message_data.get('session_used')
        )
        message.save()
        
        media_info = f", with media: {media_path}" if media_path else ""
        session_info = f" (via {message_data.get('session_used').phone})" if message_data.get('session_used') else ""
        logger.info(f"Saved message: channel '{channel.name}', message ID {message_data['message_id']}{media_info}{session_info}")
        
        return message
    except Exception as e:
        logger.error(f"Error saving message: {e}")
        logger.error(traceback.format_exc())
        return None

def _get_channels():
    try:
        channels = list(models.Channel.objects.filter(is_active=True).select_related('category', 'session').order_by('id'))
        logger.debug(f"Retrieved {len(channels)} active channels from database")
        return channels
    except Exception as e:
        logger.error(f"Error getting channels from database: {e}")
        logger.error(traceback.format_exc())
        return []

def _get_telegram_sessions():
    try:
        # Використовуємо values() для явного вказання потрібних полів, без поля needs_auth
        sessions = list(models.TelegramSession.objects.filter(is_active=True)
                        .values('id', 'phone', 'api_id', 'api_hash', 'is_active', 'session_file')
                        .order_by('id'))
        logger.debug(f"Retrieved {len(sessions)} active Telegram sessions from database")
        return sessions
    except Exception as e:
        logger.error(f"Error getting Telegram sessions from database: {e}")
        logger.error(traceback.format_exc())
        return []

def _get_session_by_id(session_id):
    if not session_id:
        return None
    try:
        # Use values() to explicitly select only the fields we need
        # This avoids accessing fields that might not exist in the database
        session_data = models.TelegramSession.objects.filter(id=session_id).values(
            'id', 'phone', 'api_id', 'api_hash', 'is_active', 'session_file'
        ).first()
        
        if not session_data:
            logger.warning(f"Telegram session with ID {session_id} not found")
            return None
            
        # Create a session object manually from the values
        session = models.TelegramSession()
        for key, value in session_data.items():
            setattr(session, key, value)
            
        return session
    except Exception as e:
        logger.error(f"Error getting Telegram session with ID {session_id}: {e}")
        logger.error(traceback.format_exc())
        return None

def _get_category_id(channel):
    """
    getting the category ID for the channel
    """
    try:
        if hasattr(channel, 'category_id') and channel.category_id:
            return channel.category_id
        elif hasattr(channel, 'category') and channel.category:
            return channel.category.id
        else:
            # Створюємо дефолтну категорію, якщо канал без категорії
            default_category, created = models.Category.objects.get_or_create(
                name="Uncategorized",
                defaults={
                    'description': 'Default category for channels',
                    'is_active': True
                }
            )
            if created:
                logger.info(f"Created default category 'Uncategorized' for channels without category")
            
            # Оновлюємо канал з дефолтною категорією
            channel.category = default_category
            channel.save()
            
            logger.info(f"Assigned default category to channel '{channel.name}'")
            return default_category.id
    except Exception as e:
        logger.error(f"Error getting/creating category for channel '{channel.name}': {e}")
        logger.error(traceback.format_exc())
        return None

save_message_to_db = sync_to_async(_save_message_to_db)
get_channels = sync_to_async(_get_channels)
get_category_id = sync_to_async(_get_category_id)
get_telegram_sessions = sync_to_async(_get_telegram_sessions)
get_session_by_id = sync_to_async(_get_session_by_id)

last_processed_message_ids = {}

# flag for stop bot
stop_event = False

# Dictionary to store Telethon clients for different sessions
telethon_clients = {}

async def get_channel_messages(client, channel_identifier):
    """
    getting messages from the specified channel
    """
    try:
        await client.get_dialogs()  # update the dialog cache
        channel = await client.get_entity(channel_identifier)
        messages = await client.get_messages(channel, 10)  # get the last 10 messages
        logger.debug(f"Received {len(messages)} messages from channel {getattr(channel, 'title', channel_identifier)}")
        return messages, channel
    except errors.ChannelInvalidError:
        logger.warning(f"Channel {channel_identifier} not found or unavailable")
        return [], None
    except errors.FloodError as e:
        logger.warning(f"FloodError when getting messages from {channel_identifier}: waiting for {e.seconds} seconds")
        await asyncio.sleep(e.seconds)
        return [], None
    except Exception as e:
        logger.error(f"Error getting messages from channel {channel_identifier}: {e}")
        logger.error(traceback.format_exc())
        return [], None

async def download_media(client, message, media_dir):
    """
    downloading media from the message and returning the path to the file
    """
    try:
        if message.media:
            # Get the absolute path for media directory
            from django.conf import settings
            
            # Use Django's MEDIA_ROOT to ensure we're saving in the right place
            absolute_media_dir = os.path.join(settings.MEDIA_ROOT, os.path.basename(media_dir))
            
            # Ensure the directory exists with proper permissions
            os.makedirs(absolute_media_dir, exist_ok=True)
            
            # Format timestamp correctly
            timestamp = message.date.strftime("%Y%m%d_%H%M%S")
            
            # Create the full path for the media file
            file_path = await message.download_media(
                file=os.path.join(absolute_media_dir, f"{message.id}_{timestamp}")
            )
            
            if file_path:
                # Verify the file actually exists
                if os.path.exists(file_path):
                    logger.info(f"Successfully downloaded media: {os.path.basename(file_path)}")
                    
                    # Make sure the file is readable
                    try:
                        with open(file_path, 'rb') as f:
                            # Just check if we can read a few bytes
                            f.read(10)
                    except Exception as e:
                        logger.error(f"Downloaded file exists but is not readable: {e}")
                        return None
                    
                    return os.path.basename(file_path)
                else:
                    logger.warning(f"Download completed but file doesn't exist: {file_path}")
                    return None
            else:
                logger.warning(f"Unable to download media for message {message.id}")
                return None
        return None
    except Exception as e:
        logger.error(f"Error downloading media: {e}")
        logger.error(traceback.format_exc())
        return None

async def save_message_to_data(message, channel, queue, category_id=None, client=None, session=None):
    """
    saving the message and sending information to the queue
    """
    try:        
        # data about media
        media_type = None
        media_file = None
        
        # determine the type of media and download it
        if message.media and client:
            if isinstance(message.media, MessageMediaPhoto):
                media_type = "photo"
                media_file = await download_media(client, message, "messages")
                logger.info(f"Media type: photo, file: {media_file}")
            elif isinstance(message.media, MessageMediaDocument):
                if message.media.document.mime_type.startswith('video'):
                    media_type = "video"
                elif message.media.document.mime_type.startswith('image'):
                    media_type = "gif" if message.media.document.mime_type == 'image/gif' else "image"
                else:
                    media_type = "document"
                media_file = await download_media(client, message, "messages")
                logger.info(f"Media type: {media_type}, file: {media_file}")
            elif isinstance(message.media, MessageMediaWebPage):
                media_type = "webpage"
                logger.info(f"Media type: webpage")
        
        # get the channel name
        channel_name = getattr(channel, 'title', None) or getattr(channel, 'name', 'Unknown channel')
        channel_id = getattr(message.peer_id, 'channel_id', None)
        
        if not channel_id:
            logger.warning(f"No channel_id in message {message.id} from {channel_name}")
            channel_id = 0
        
        # Handle the date - always ensure it's a datetime object or properly formatted string
        message_date = message.date
        from datetime import datetime
        
        if isinstance(message_date, datetime):
            # Format datetime as string
            formatted_date = message_date.strftime("%Y-%m-%d %H:%M:%S")
        elif isinstance(message_date, str):
            # Try to parse the string to ensure it's a valid date format
            try:
                parsed_date = datetime.strptime(message_date, "%Y-%m-%d %H:%M:%S")
                formatted_date = message_date  # Already correct format
            except ValueError:
                # If the date string is in a different format, try to parse it
                try:
                    # Try common formats
                    for fmt in ["%Y-%m-%d", "%d.%m.%Y %H:%M", "%d/%m/%Y", "%Y/%m/%d %H:%M:%S"]:
                        try:
                            parsed_date = datetime.strptime(message_date, fmt)
                            formatted_date = parsed_date.strftime("%Y-%m-%d %H:%M:%S")
                            break
                        except ValueError:
                            continue
                    else:
                        # If no format matches, use current time
                        logger.warning(f"Could not parse date: {message_date}, using current time")
                        formatted_date = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                except Exception as e:
                    logger.error(f"Error parsing date {message_date}: {e}")
                    formatted_date = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        else:
            # If message_date is something else, use current time
            logger.warning(f"Unexpected date type: {type(message_date)}, using current time")
            formatted_date = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        # save the message
        message_info = {
            'text': message.text or "",
            'media': f"messages/{media_file}" if media_file else "",
            'media_type': media_type if media_type else None,
            'message_id': message.id,
            'channel_id': channel_id,
            'channel_name': channel_name,
            'link': f"https://t.me/c/{channel_id}/{message.id}" if channel_id else "#",
            'date': formatted_date,
            'session_used': session
        }
        
        # save to DB
        await save_message_to_db(message_info)
        
        # send to queue
        if queue:
            try:
                queue.put({
                    'message_info': message_info, 
                    'category_id': category_id
                })
            except Exception as e:
                logger.error(f"Error putting message in queue: {e}")
                logger.error(traceback.format_exc())
        
        session_info = f" (via {session.phone})" if session else ""
        logger.info(f"Saved message {message.id} from channel '{channel_name}'{session_info}")

    except Exception as e:
        logger.error(f"Error saving message: {e}")
        logger.error(traceback.format_exc())

def extract_username_from_link(link):
    """extract username/channel from telegram link"""
    username_match = re.search(r'https?://(?:t|telegram)\.me/([^/]+)', link)
    if username_match:
        return username_match.group(1)
    return None

async def initialize_client(session_id=None, session_filename=None):
    """Initialize a Telethon client for a specific session"""
    # If session_id is provided, look up the DB record
    if session_id:
        session = await get_session_by_id(session_id)
        if not session:
            logger.error(f"No session found in database with ID {session_id}")
            return None, None
            
        # Try to use the session file specified in the database
        if session.session_file and os.path.exists(f"{session.session_file}.session"):
            session_filename = session.session_file
            logger.info(f"Found session file from database: {session_filename}")
        else:
            # Look for session files with various naming patterns
            potential_session_files = [
                f"telethon_session_{session_id}",
                f"telethon_session_{session.phone.replace('+', '')}",
                f"telethon_user_session_{session_id}",
                f"session_{session_id}",
                f"session_user_{session_id}",
            ]
            
            # Check different directories
            session_dirs = [".", "data/sessions", "sessions", "/app/data/sessions"]
            
            # First, try exact matches for this session
            for directory in session_dirs:
                if not os.path.exists(directory):
                    continue
                    
                for base_name in potential_session_files:
                    full_path = os.path.join(directory, base_name)
                    if os.path.exists(f"{full_path}.session"):
                        session_filename = full_path
                        logger.info(f"Found session file: {full_path}.session")
                        break
                        
                if session_filename:
                    break
            
            # If still no session file, verify the session
            if not session_filename:
                logger.warning(f"No session file found for session ID {session_id} ({session.phone})")
                
                # Create a new session file if we have the phone number
                if session.phone:
                    # First verify if we already have valid sessions with different names
                    for directory in session_dirs:
                        if not os.path.exists(directory):
                            continue
                            
                        for file in os.listdir(directory):
                            if file.endswith('.session'):
                                # Check if this session is valid
                                session_path = os.path.join(directory, file[:-8])  # Remove .session
                                is_valid, user_info = await verify_session(session_path, API_ID, API_HASH)
                                if is_valid:
                                    session_filename = session_path
                                    logger.info(f"Found valid session: {session_path}")
                                    
                                    # Update the session in the database
                                    session.session_file = session_filename
                                    await sync_to_async(session.save)()
                                    break
                                    
                        if session_filename:
                            break
                    
                    # If still no valid session, create one
                    if not session_filename:
                        logger.info(f"Creating new session for {session.phone}")
                        new_session_name = f"telethon_session_{session.phone.replace('+', '')}"
                        
                        # Create non-interactively since we're in a web process
                        # Note: This will likely fail as it requires user interaction for the code
                        # But we need to handle this case and inform the user
                        success = await create_session_file(
                            session.phone, 
                            API_ID, 
                            API_HASH, 
                            new_session_name,
                            interactive=False
                        )
                        
                        if success:
                            session_filename = new_session_name
                            logger.info(f"Successfully created new session: {new_session_name}")
                        else:
                            logger.error(f"Failed to create session automatically. Manual authentication required.")
                            try:
                                # Update session in a more controlled way to avoid null created_at
                                @sync_to_async
                                def update_session_safely():
                                    # Make sure session exists and get a fresh copy to avoid null fields
                                    try:
                                        current_session = models.TelegramSession.objects.get(id=session_id)
                                        if hasattr(current_session, 'needs_auth'):
                                            current_session.needs_auth = True
                                        current_session.session_file = None
                                        current_session.save(update_fields=['session_file', 'needs_auth'] 
                                                           if hasattr(current_session, 'needs_auth') 
                                                           else ['session_file'])
                                        return True
                                    except Exception as e:
                                        logger.error(f"Error safely updating session: {e}")
                                        return False
                                        
                                update_success = await update_session_safely()
                                if not update_success:
                                    logger.error(f"Failed to update session in database. Will try to continue with defaults.")
                            except Exception as e:
                                logger.error(f"Error updating session: {e}")
                            return None, None
        
    # Fall back to default session files if no specific session was found
    if not session_filename:
        for default_file in ['telethon_user_session', 'telethon_session', 'anon']:
            if os.path.exists(f'{default_file}.session'):
                session_filename = default_file
                logger.info(f"Using default session file: {default_file}.session")
                break
                
        # As a last resort, look for any .session file
        if not session_filename:
            for file in os.listdir('.'):
                if file.endswith('.session'):
                    session_filename = file[:-8]  # Remove .session extension
                    logger.info(f"Using available session file: {file}")
                    break
                    
        if not session_filename:
            logger.error("No session file found")
            return None, None
    
    # Verify the session before using it
    is_valid, user_info = await verify_session(session_filename, API_ID, API_HASH)
    if not is_valid:
        logger.error(f"Session {session_filename} exists but is not authorized")
        return None, None
    
    logger.info(f"Using verified session: {session_filename}")
    
    # Session file with a unique suffix to avoid conflicts
    unique_session = f"{session_filename}_{session_id or 'default'}_{os.getpid()}"
    
    try:
        # Copy the session file to prevent concurrent access
        if os.path.exists(f'{session_filename}.session'):
            import shutil
            try:
                shutil.copy2(f'{session_filename}.session', f'{unique_session}.session')
                logger.debug(f"Created temporary session file: {unique_session}.session")
            except Exception as e:
                logger.error(f"Error copying session file: {e}")
                # Continue with original file if copy fails
                unique_session = session_filename
        else:
            unique_session = session_filename
        
        # Create Telethon client with the session file
        client = TelegramClient(unique_session, API_ID, API_HASH)
        
        # Connect with timeout and retry logic
        max_retries = 3
        retry_count = 0
        connected = False
        
        while retry_count < max_retries and not connected:
            try:
                # Connect with timeout handling
                connect_task = asyncio.create_task(client.connect())
                try:
                    await asyncio.wait_for(connect_task, timeout=15)  # 15 seconds timeout
                    connected = True
                except asyncio.TimeoutError:
                    retry_count += 1
                    backoff = retry_count * 2  # Exponential backoff
                    logger.warning(f"Connection timeout for session {session_filename}. Retry {retry_count}/{max_retries} in {backoff}s")
                    
                    if not connect_task.done():
                        connect_task.cancel()
                        
                    if retry_count < max_retries:
                        await asyncio.sleep(backoff)
                    else:
                        logger.error(f"Failed to connect after {max_retries} attempts for session {session_filename}")
                        await client.disconnect()
                        return None, None
                        
            except Exception as e:
                retry_count += 1
                backoff = retry_count * 2
                logger.error(f"Error connecting to Telegram for session {session_filename}: {e}")
                logger.error(traceback.format_exc())
                
                if retry_count < max_retries:
                    logger.info(f"Retrying in {backoff} seconds... ({retry_count}/{max_retries})")
                    await asyncio.sleep(backoff)
                else:
                    logger.error(f"Failed to connect after {max_retries} attempts")
                    try:
                        await client.disconnect()
                    except:
                        pass
                    return None, None
        
        # Get user info
        try:
            me = await client.get_me()
            logger.info(f"Initialized client for session {session_filename} as: {me.first_name} (@{me.username or 'No username'}) [ID: {me.id}]")
            
            # If we have a session_id, update the DB record with username info
            if session_id:
                @sync_to_async
                def update_session_info():
                    try:
                        session = models.TelegramSession.objects.get(id=session_id)
                        if not session.session_file or session.session_file != session_filename:
                            session.session_file = session_filename
                            session.save()
                            logger.info(f"Updated session file path in database: {session_filename}")
                    except Exception as e:
                        logger.error(f"Error updating session info: {e}")
                        logger.error(traceback.format_exc())
                
                await update_session_info()
            
            return client, me
        except Exception as e:
            logger.error(f"Error getting account information for session {session_filename}: {e}")
            logger.error(traceback.format_exc())
            await client.disconnect()
            return None, None
            
    except Exception as e:
        logger.error(f"Error initializing client for session {session_filename}: {e}")
        logger.error(traceback.format_exc())
        try:
            await client.disconnect()
        except:
            pass
        
        # Clean up temporary session file if it exists and differs from original
        if unique_session != session_filename and os.path.exists(f'{unique_session}.session'):
            try:
                os.remove(f'{unique_session}.session')
                logger.debug(f"Removed temporary session file: {unique_session}.session")
            except Exception as e:
                logger.error(f"Error removing temporary session file: {e}")
                
        return None, None

async def telethon_task(queue):
    global stop_event, telethon_clients
    """
    background task for parsing messages with Telethon.
    """
    try:
        # Get all active sessions from the database
        sessions = await get_telegram_sessions()
        
        if not sessions:
            logger.warning("No active Telegram sessions found in the database")
            # Try to initialize a default client
            default_client, default_me = await initialize_client()
            if default_client:
                telethon_clients['default'] = {
                    'client': default_client,
                    'user': default_me,
                    'session_id': None
                }
                logger.info("Initialized default client as no sessions were found in database")
            else:
                logger.error("Failed to initialize default client and no sessions in database.")
                logger.info("Parser will keep running but won't be able to fetch messages until a session is available")
                # Instead of returning, keep running and periodically check for new sessions
                while not stop_event:
                    await asyncio.sleep(60)  # Check every minute
                    new_sessions = await get_telegram_sessions()
                    if new_sessions:
                        logger.info(f"Found {len(new_sessions)} new sessions. Restarting parser...")
                        return await telethon_task(queue)  # Restart the task with new sessions
        else:
            # Initialize clients for all active sessions
            initialized_count = 0
            for session in sessions:
                client, me = await initialize_client(session_id=session['id'])
                if client:
                    telethon_clients[str(session['id'])] = {
                        'client': client,
                        'user': me,
                        'session_id': session['id'],
                        'session': session
                    }
                    initialized_count += 1
                    logger.info(f"Initialized client for session {session['phone']} (ID: {session['id']})")
                else:
                    logger.error(f"Failed to initialize client for session {session['phone']} (ID: {session['id']})")
            
            # If no clients were initialized, try to find any valid session files
            if not telethon_clients:
                logger.warning("No clients were initialized from database sessions. Looking for any valid session files...")
                
                # Look for any session files in common directories
                session_dirs = [".", "data/sessions", "sessions", "/app/data/sessions"]
                for directory in session_dirs:
                    if not os.path.exists(directory):
                        continue
                        
                    for file in os.listdir(directory):
                        if file.endswith('.session'):
                            # Check if this session is valid
                            session_path = os.path.join(directory, file[:-8])  # Remove .session
                            is_valid, user_info = await verify_session(session_path, API_ID, API_HASH)
                            if is_valid:
                                # Use it as a fallback
                                fallback_client = TelegramClient(session_path, API_ID, API_HASH)
                                await fallback_client.connect()
                                if await fallback_client.is_user_authorized():
                                    me = await fallback_client.get_me()
                                    telethon_clients['fallback'] = {
                                        'client': fallback_client,
                                        'user': me,
                                        'session_id': None
                                    }
                                    logger.info(f"Initialized fallback client from {session_path}")
                                    break
                    
                    if telethon_clients:
                        break
            
            # If still no clients, try with a default session
            if not telethon_clients:
                default_client, default_me = await initialize_client()
                if default_client:
                    telethon_clients['default'] = {
                        'client': default_client,
                        'user': default_me,
                        'session_id': None
                    }
                    logger.info("Initialized default client as fallback")
                else:
                    logger.error("Failed to initialize any client. Parser will keep running but won't be able to fetch messages.")
                    # Instead of returning, keep running and periodically check for new sessions
                    while not stop_event:
                        await asyncio.sleep(60)  # Check every minute
                        new_sessions = await get_telegram_sessions()
                        if new_sessions:
                            logger.info(f"Found {len(new_sessions)} new sessions. Restarting parser...")
                            return await telethon_task(queue)  # Restart the task with new sessions
        
        logger.info("====== Telethon Parser started ======")
        logger.info(f"Initialized {len(telethon_clients)} client(s)")

        while not stop_event:
            try:
                channels = await get_channels()
                if not channels:
                    logger.warning("No channels found for parsing. Waiting before retrying...")
                    await asyncio.sleep(30)
                    continue
                
                logger.info(f"Found {len(channels)} channels for parsing")
                
                active_channels = sum(1 for channel in channels if channel.is_active)
                logger.info(f"Active channels: {active_channels}/{len(channels)}")
                
                for channel in channels:
                    # Check if stop event was set during iteration
                    if stop_event:
                        break
                        
                    if not channel.is_active:
                        logger.debug(f"Channel '{channel.name}' is not active for parsing")
                        continue
                        
                    try:
                        # Get the appropriate client for this channel
                        channel_session_id = getattr(channel, 'session_id', None)
                        client_info = None
                        
                        if channel_session_id and str(channel_session_id) in telethon_clients:
                            # Use the channel's assigned session
                            client_info = telethon_clients[str(channel_session_id)]
                            logger.debug(f"Using assigned session {channel_session_id} for channel '{channel.name}'")
                        elif 'default' in telethon_clients:
                            # Use the default client if available
                            client_info = telethon_clients['default']
                            logger.debug(f"Using default session for channel '{channel.name}'")
                        elif telethon_clients:
                            # Use the first available client
                            first_key = next(iter(telethon_clients))
                            client_info = telethon_clients[first_key]
                            logger.debug(f"Using first available session for channel '{channel.name}'")
                        else:
                            logger.error(f"No client available for channel '{channel.name}'")
                            continue
                        
                        client = client_info['client']
                        session = client_info.get('session')
                        
                        # use channel link
                        channel_link = channel.url
                        
                        if not channel_link or not channel_link.startswith('https://t.me/'):
                            logger.warning(f"Channel '{channel.name}' has no valid link")
                            continue
                                
                        # first try to join channel
                        try:
                            # extract username from link
                            username = extract_username_from_link(channel_link)
                            if username:
                                entity = await client.get_entity(username)
                                await client(JoinChannelRequest(entity))
                                logger.info(f"Successfully joined channel: @{username}")
                            else:
                                logger.warning(f"Unable to get identifier from link: {channel_link}")
                        except errors.FloodWaitError as e:
                            hours, remainder = divmod(e.seconds, 3600)
                            minutes, seconds = divmod(remainder, 60)
                            time_str = f"{hours}h {minutes}m {seconds}s" if hours > 0 else f"{minutes}m {seconds}s"
                            logger.warning(f"Flood wait for {time_str} when joining channel. Skipping.")
                            continue
                        except Exception as e:
                            logger.error(f"Error joining channel {channel_link}: {e}")
                            logger.error(traceback.format_exc())

                        # Get messages with retry logic
                        retry_count = 0
                        max_retries = 3
                        messages = None
                        tg_channel = None
                        
                        while retry_count < max_retries and not messages:
                            try:
                                # get messages from channel
                                messages, tg_channel = await get_channel_messages(client, channel_link)
                                if not messages or not tg_channel:
                                    retry_count += 1
                                    if retry_count < max_retries:
                                        logger.warning(f"Retry {retry_count}/{max_retries} getting messages from '{channel.name}'")
                                        await asyncio.sleep(retry_count * 2)  # Exponential backoff
                                    else:
                                        logger.error(f"Failed to get messages from '{channel.name}' after {max_retries} attempts")
                            except Exception as e:
                                logger.error(f"Error getting messages from channel '{channel.name}': {e}")
                                logger.error(traceback.format_exc())
                                retry_count += 1
                                if retry_count < max_retries:
                                    await asyncio.sleep(retry_count * 2)
                                
                        if messages and tg_channel:
                            # check if message is new
                            latest_message = messages[0]
                            channel_identifier = f"{channel_link}_{client_info['session_id'] if client_info['session_id'] else 'default'}"
                            last_message_id = last_processed_message_ids.get(channel_identifier)
                            
                            if not last_message_id or latest_message.id > last_message_id:
                                # get category id
                                category_id = None
                                if hasattr(channel, 'category_id'):
                                    category_id = await get_category_id(channel)
                                # send message to save
                                session_info = f" (via {session.phone})" if session else ""
                                logger.info(f"New message in channel '{channel.name}' [ID: {latest_message.id}]{session_info}")
                                await save_message_to_data(latest_message, channel, queue, category_id, client, session)
                                last_processed_message_ids[channel_identifier] = latest_message.id
                            else:
                                logger.debug(f"Message from channel '{channel.name}' already processed")
                        else:
                            logger.warning(f"Unable to get messages from channel: '{channel.name}'")

                    except errors.FloodError as e:
                        hours, remainder = divmod(e.seconds, 3600)
                        minutes, seconds = divmod(remainder, 60)
                        time_str = f"{hours}h {minutes}m {seconds}s" if hours > 0 else f"{minutes}m {seconds}s"
                        logger.warning(f"Rate limit exceeded. Waiting {time_str}")
                        await asyncio.sleep(e.seconds)

                    except Exception as e:
                        logger.error(f"Error in telethon_task for channel '{channel.name}': {e}")
                        logger.error(traceback.format_exc())

                    # Small sleep between processing channels to avoid rate limiting
                    await asyncio.sleep(5)
                    
                # End of channels loop
                if stop_event:
                    break
                    
                logger.info("Parsing cycle completed. Waiting 30 seconds for the next cycle...")
                await asyncio.sleep(30)  # pause between checks
                
            except Exception as e:
                logger.error(f"Error reading or processing channels: {e}")
                logger.error(traceback.format_exc())
                await asyncio.sleep(30)  # Wait before retrying
                
    except Exception as e:
        logger.error(f"Error in telethon_task: {e}")
        logger.error(traceback.format_exc())
    finally:
        # Ensure all clients are properly disconnected
        for session_id, client_info in list(telethon_clients.items()):
            if client_info and 'client' in client_info:
                try:
                    logger.info(f"Disconnecting Telethon client for session {session_id}...")
                    client = client_info['client']
                    # Use an explicit timeout for disconnecting to avoid hanging
                    disconnect_task = asyncio.create_task(client.disconnect())
                    try:
                        await asyncio.wait_for(disconnect_task, timeout=5)
                        logger.info(f"Telethon client for session {session_id} disconnected")
                    except asyncio.TimeoutError:
                        logger.warning(f"Timeout disconnecting client for session {session_id}")
                    except Exception as e:
                        logger.error(f"Error disconnecting client for session {session_id}: {e}")
                except Exception as e:
                    logger.error(f"Error disconnecting client for session {session_id}: {e}")

def handle_interrupt(signum, frame):
    global stop_event
    logger.info("Received signal to stop Telethon...")
    stop_event = True

def telethon_worker_process(queue):
    """
    start background task Telethon in separate process.
    """
    global stop_event
    stop_event = False
    
    logger.info("Starting Telethon parser process...")
    signal.signal(signal.SIGINT, handle_interrupt)
    signal.signal(signal.SIGTERM, handle_interrupt)

    # Run the telethon task in a new event loop
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        loop.run_until_complete(telethon_task(queue))
    except KeyboardInterrupt:
        logger.info("Parser process completed by user (KeyboardInterrupt)")
        stop_event = True
    except Exception as e:
        logger.error(f"Error in parser process: {e}")
        logger.error(traceback.format_exc())
    finally:
        # Cancel pending tasks
        pending_tasks = [task for task in asyncio.all_tasks(loop) if not task.done()]
        
        if pending_tasks:
            # Cancel all pending tasks
            logger.info(f"Cancelling {len(pending_tasks)} pending tasks...")
            for task in pending_tasks:
                task.cancel()
                
            # Give tasks a chance to respond to cancellation
            try:
                loop.run_until_complete(asyncio.gather(*pending_tasks, return_exceptions=True))
            except Exception as e:
                logger.error(f"Error during task cancellation: {e}")
        
        # Close the loop
        try:
            loop.run_until_complete(loop.shutdown_asyncgens())
            loop.close()
            logger.info("Event loop closed")
        except Exception as e:
            logger.error(f"Error closing event loop: {e}")
            
        logger.info("Parser process completed")