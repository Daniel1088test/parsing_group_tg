import asyncio
import json
import os
import signal
import re
import logging
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

# import models
from admin_panel import models

def _save_message_to_db(message_data):
    """
    save message to db
    """
    try:
        # Try to find channel by exact name first
        channel = None
        channel_name = message_data['channel_name']
        channel_username = None
        channel_id = message_data.get('channel_id')
        
        # Extract username from link if available
        if 'link' in message_data:
            channel_username = extract_username_from_link(message_data['link'])
        
        # Спочатку шукаємо канал за Telegram channel_id
        if channel_id:
            matching_channels = list(models.Channel.objects.filter(
                models.Q(url__contains=str(channel_id))
            ))
            if matching_channels:
                channel = matching_channels[0]
                logger.info(f"Found channel by Telegram ID: {channel.name} (ID: {channel.id})")
        
        # Якщо канал не знайдено за ID, шукаємо за username
        if not channel and channel_username:
            matching_channels = list(models.Channel.objects.filter(
                models.Q(url__contains=channel_username)
            ))
            if matching_channels:
                channel = matching_channels[0]
                logger.info(f"Found channel by username: {channel.name} (ID: {channel.id})")
        
        # Якщо канал не знайдено, шукаємо за назвою
        if not channel:
            try:
                # Перевіряємо різні варіанти написання назви каналу
                channel = models.Channel.objects.get(name=channel_name)
                logger.info(f"Found channel by exact name: {channel.name} (ID: {channel.id})")
            except models.Channel.DoesNotExist:
                logger.debug(f"Channel with exact name {channel_name} not found")
                
                # Спробуємо знайти за схожою назвою (відрізняється тільки суфіксом)
                base_name = channel_name.split()[0]  # Беремо перше слово назви
                matching_channels = list(models.Channel.objects.filter(
                    models.Q(name__startswith=base_name)
                ))
                
                if matching_channels:
                    channel = matching_channels[0]
                    logger.info(f"Found channel by similar name: {channel.name} (ID: {channel.id})")
        
        # Якщо канал не знайдено, створюємо новий
        if not channel:
            # Create new channel with default category
            default_category, _ = models.Category.objects.get_or_create(name="Uncategorized")
            
            # Формуємо URL для каналу
            channel_url = ""
            if channel_username:
                channel_url = f"https://t.me/{channel_username}"
            elif channel_id:
                channel_url = f"https://t.me/c/{channel_id}"
                
            # Створюємо канал
            channel = models.Channel(
                name=channel_name,
                url=channel_url,
                category=default_category,
                is_active=True
            )
            
            # Встановлюємо сесію, якщо її передано
            if message_data.get('session_used'):
                channel.session = message_data.get('session_used')
                
            channel.save()
            logger.info(f"Created new channel: {channel.name} (ID: {channel.id})")
        
        # Оновлюємо поля каналу, якщо отримано нову інформацію
        updated = False
        if channel_username and not channel.url:
            channel.url = f"https://t.me/{channel_username}"
            updated = True
        
        # Якщо канал не має сесії, але ми маємо сесію, зберігаємо її
        if not channel.session and message_data.get('session_used'):
            channel.session = message_data.get('session_used')
            updated = True
            
        # Зберігаємо зміни в каналі, якщо вони є
        if updated:
            channel.save()
            logger.info(f"Updated channel information: {channel.name} (ID: {channel.id})")
        
        # Створюємо повідомлення
        message = models.Message(
            text=message_data['text'],
            media=message_data['media'],
            media_type=message_data['media_type'],
            telegram_message_id=message_data['message_id'],
            telegram_channel_id=message_data['channel_id'],
            telegram_link=message_data['link'],
            channel=channel,
            created_at=message_data['date'],
            session_used=message_data.get('session_used')
        )
        message.save()
        
        # Логуємо збереження повідомлення
        session_info = f" (via {message_data.get('session_used').phone})" if message_data.get('session_used') else ""
        logger.info(f"Saved message: channel '{channel.name}', message ID {message_data['message_id']}{session_info}")
        return message
    except Exception as e:
        logger.error(f"Error saving message: {e}")
        import traceback
        logger.error(f"Error traceback: {traceback.format_exc()}")
        return None

def _get_channels():
    channels = list(models.Channel.objects.all().select_related('category', 'session').order_by('id'))
    return channels

def _get_telegram_sessions():
    sessions = list(models.TelegramSession.objects.filter(is_active=True).order_by('id'))
    return sessions

def _get_session_by_id(session_id):
    if not session_id:
        return None
    try:
        return models.TelegramSession.objects.get(id=session_id)
    except models.TelegramSession.DoesNotExist:
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
            logger.warning(f"Channel '{channel.name}' has no associated category")
            return None
    except Exception as e:
        logger.error(f"Error getting category for channel '{channel.name}': {e}")
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
    except Exception as e:
        logger.error(f"Error getting messages from channel {channel_identifier}: {e}")
        return [], None

async def download_media(client, message, media_dir):
    """
    downloading media from the message and returning the path to the file
    """
    try:
        if message.media:
            # Переконуємося, що папка для медіа існує
            os.makedirs(media_dir, exist_ok=True)
            
            # Генеруємо унікальне ім'я файлу з timestamp та ID повідомлення
            timestamp = message.date.strftime("%Y%m%d_%H%M%S")
            file_name = f"{message.id}_{timestamp}"
            file_path = os.path.join(media_dir, file_name)
            
            # Завантажуємо медіа-файл
            downloaded_path = await message.download_media(file=file_path)
            
            if downloaded_path:
                # Перевіряємо, чи файл був успішно завантажений
                if os.path.exists(downloaded_path):
                    # Отримуємо лише ім'я файлу без шляху
                    relative_path = os.path.relpath(downloaded_path, os.getcwd())
                    logger.info(f"Downloaded media: {relative_path}")
                    return relative_path
                else:
                    logger.warning(f"Downloaded path returned but file doesn't exist: {downloaded_path}")
                    return None
            else:
                logger.warning(f"Unable to download media for message {message.id}")
                return None
        return None
    except Exception as e:
        logger.error(f"Error downloading media: {e}")
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
                media_file = await download_media(client, message, "media/messages")
                logger.debug(f"Media type: photo, file: {media_file}")
            elif isinstance(message.media, MessageMediaDocument):
                if message.media.document.mime_type.startswith('video'):
                    media_type = "video"
                elif message.media.document.mime_type.startswith('image'):
                    media_type = "gif" if message.media.document.mime_type == 'image/gif' else "image"
                else:
                    media_type = "document"
                media_file = await download_media(client, message, "media/messages")
                logger.debug(f"Media type: {media_type}, file: {media_file}")
            elif isinstance(message.media, MessageMediaWebPage):
                media_type = "webpage"
                logger.debug(f"Media type: webpage")
        
        # get the channel name
        channel_name = getattr(channel, 'title', None) or getattr(channel, 'name', 'Unknown channel')
        
        # save the message
        message_info = {
            'text': message.text,
            'media': media_file if media_file else "",  # Використовуємо повний шлях, повернутий download_media
            'media_type': media_type if media_type else None,
            'message_id': message.id,
            'channel_id': message.peer_id.channel_id,
            'channel_name': channel_name,
            'link': f"https://t.me/c/{message.peer_id.channel_id}/{message.id}",
            'date': message.date.strftime("%Y-%m-%d %H:%M:%S"),
            'session_used': session
        }
        
        # save to DB
        await save_message_to_db(message_info)
        
        # send to queue
        queue.put({
            'message_info': message_info, 
            'category_id': category_id
        })
        
        session_info = f" (via {session.phone})" if session else ""
        logger.info(f"Saved message {message.id} from channel '{channel_name}'{session_info}")

    except Exception as e:
        logger.error(f"Error saving message: {e}")
        import traceback
        error_traceback = traceback.format_exc()
        logger.error(f"Error traceback: {error_traceback}")

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
        if session and session.session_file:
            session_filename = session.session_file
            # If it's a custom session file from our DB
            if not os.path.exists(f'{session_filename}.session'):
                # Fall back to default session files
                if os.path.exists('telethon_user_session.session'):
                    session_filename = 'telethon_user_session'
                elif os.path.exists('telethon_session.session'):
                    session_filename = 'telethon_session'
                else:
                    logger.error(f"No session file found for session ID {session_id}")
                    return None, None
        else:
            # Default session files if the session record doesn't specify one
            if os.path.exists('telethon_user_session.session'):
                session_filename = 'telethon_user_session'
            elif os.path.exists('telethon_session.session'):
                session_filename = 'telethon_session'
            else:
                logger.error(f"No default session file found")
                return None, None
    elif not session_filename:
        # Default to checking normal session files
        if os.path.exists('telethon_user_session.session'):
            session_filename = 'telethon_user_session'
        elif os.path.exists('telethon_session.session'):
            session_filename = 'telethon_session'
        else:
            logger.error("No session file found")
            return None, None
    
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
        
        # Check authorization
        if not await client.is_user_authorized():
            logger.error(f"Session {session_filename} exists but is not authorized")
            await client.disconnect()
            return None, None
            
        # Get user info
        try:
            me = await client.get_me()
            logger.info(f"Initialized client for session {session_filename} as: {me.first_name} (@{me.username}) [ID: {me.id}]")
            
            # If we have a session_id, update the DB record with username info
            if session_id:
                @sync_to_async
                def update_session_info():
                    try:
                        session = models.TelegramSession.objects.get(id=session_id)
                        if not session.session_file:
                            session.session_file = session_filename
                            session.save()
                    except Exception as e:
                        logger.error(f"Error updating session info: {e}")
                
                await update_session_info()
            
            # Add proper session loading with password if needed
            if client:
                try:
                    # Ensure we're properly connected
                    if not client.is_connected():
                        await client.connect()
                        
                    # Force authorization check
                    if not await client.is_user_authorized():
                        logger.error(f"Session exists but not authorized. Try recreating the session.")
                        # You might need to handle 2FA here if your account has it
                    else:
                        logger.info("Successfully authorized with session")
                except Exception as e:
                    logger.error(f"Error during client connection: {e}")
            
            return client, me
        except Exception as e:
            logger.error(f"Error getting account information for session {session_filename}: {e}")
            await client.disconnect()
            return None, None
            
    except Exception as e:
        logger.error(f"Error initializing client for session {session_filename}: {e}")
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

async def telethon_task(queue, pre_initialized_client=None):
    global stop_event, telethon_clients
    """
    background task for parsing messages with Telethon.
    """
    try:
        # If we have a pre-initialized client, try to use it (carefully)
        if pre_initialized_client:
            logger.info("Using pre-initialized client from run.py")
            session_filename = None
            
            try:
                # Try to extract session information without making API calls
                # that would require the event loop from the other process
                if hasattr(pre_initialized_client, 'session'):
                    session_filename = getattr(pre_initialized_client.session, 'filename', None)
                    
                if session_filename:
                    logger.info(f"Extracted session filename from pre-initialized client: {session_filename}")
                    
                    # Initialize a NEW client with this session in our event loop
                    # instead of trying to reuse the pre-initialized client
                    client, me = await initialize_client(session_filename=session_filename)
                    
                    if client:
                        telethon_clients['default'] = {
                            'client': client, 
                            'user': me,
                            'session_id': None
                        }
                        logger.info(f"Successfully initialized new client with session {session_filename}: {me.first_name} (@{me.username}) [ID: {me.id}]")
                    else:
                        logger.error(f"Failed to initialize client with session {session_filename}, will try other sessions")
                else:
                    logger.warning("Could not extract session filename from pre-initialized client")
            except Exception as e:
                logger.error(f"Error extracting session info from pre-initialized client: {e}")
                import traceback
                logger.error(f"Traceback: {traceback.format_exc()}")
                # Continue below to try initializing from sessions
        
        # If we don't have any clients yet (or pre-init processing failed), proceed with normal initialization
        if not telethon_clients:
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
                    logger.error("Failed to initialize default client and no sessions in database. Parser cannot run.")
                    return
            else:
                # Initialize clients for all active sessions
                for session in sessions:
                    client, me = await initialize_client(session_id=session.id)
                    if client:
                        telethon_clients[str(session.id)] = {
                            'client': client,
                            'user': me,
                            'session_id': session.id,
                            'session': session
                        }
                        logger.info(f"Initialized client for session {session.phone} (ID: {session.id})")
                    else:
                        logger.error(f"Failed to initialize client for session {session.phone} (ID: {session.id})")
                
                # If no clients were initialized, try with default session
                if not telethon_clients:
                    logger.warning("No clients were initialized from sessions. Trying default session.")
                    default_client, default_me = await initialize_client()
                    if default_client:
                        telethon_clients['default'] = {
                            'client': default_client,
                            'user': default_me,
                            'session_id': None
                        }
                        logger.info("Initialized default client as fallback")
                    else:
                        logger.error("Failed to initialize any client. Parser cannot run.")
                        return
        
        # Main parsing loop
        logger.info("Starting to receive updates...")
        
        while not stop_event:
            try:
                # Get channels from database
                channels = await get_channels()
                
                if not channels:
                    logger.warning("No channels found in the database")
                    await asyncio.sleep(60)  # Wait 1 minute before checking again
                    continue
                
                # Iterate through each channel and collect messages
                for channel in channels:
                    if stop_event:
                        break
                        
                    # Determine which client to use for this channel
                    client_info = None
                    
                    # Use channel-specific session if available
                    if channel.session and channel.session.is_active:
                        session_id = str(channel.session.id)
                        client_info = telethon_clients.get(session_id)
                        if not client_info:
                            logger.warning(f"Channel {channel.name} has session {channel.session.phone} (ID: {channel.session.id}) but no client initialized for it")
                    
                    # Fall back to default client if no channel-specific client or it failed
                    if not client_info:
                        client_info = telethon_clients.get('default')
                        if not client_info:
                            logger.error(f"No default client available for channel {channel.name}. Skipping.")
                            continue
                    
                    # Get client and associated information
                    client = client_info['client']
                    session = client_info.get('session')
                    
                    try:
                        # Get identifier for the channel
                        if channel.url:
                            identifier = channel.url
                            # Extract username if it's a t.me link
                            username = extract_username_from_link(identifier)
                            if username:
                                identifier = username
                        else:
                            identifier = channel.name
                            
                        logger.debug(f"Getting messages for channel: {identifier}")
                        
                        # Try to join the channel if not already joined
                        try:
                            channel_entity = await client.get_entity(identifier)
                            try:
                                await client(JoinChannelRequest(channel_entity))
                                logger.info(f"Joined channel {getattr(channel_entity, 'title', identifier)}")
                                
                                # Update channel information in the database
                                @sync_to_async
                                def update_channel_info():
                                    try:
                                        # Get current channel from database
                                        db_channel = models.Channel.objects.get(id=channel.id)
                                        
                                        # Update channel information
                                        updated = False
                                        
                                        # Update title if different
                                        if hasattr(channel_entity, 'title') and channel_entity.title:
                                            if db_channel.title != channel_entity.title:
                                                db_channel.title = channel_entity.title
                                                updated = True
                                                
                                        # Update telegram_id if we have it
                                        if hasattr(channel_entity, 'id') and channel_entity.id:
                                            if not db_channel.telegram_id or db_channel.telegram_id != str(channel_entity.id):
                                                db_channel.telegram_id = str(channel_entity.id)
                                                updated = True
                                                
                                        # Update username if we have it
                                        if hasattr(channel_entity, 'username') and channel_entity.username:
                                            if not db_channel.telegram_username or db_channel.telegram_username != channel_entity.username:
                                                db_channel.telegram_username = channel_entity.username
                                                updated = True
                                                
                                                # Also update URL if username is available
                                                if not db_channel.url or 't.me' not in db_channel.url:
                                                    db_channel.url = f"https://t.me/{channel_entity.username}"
                                                    updated = True
                                        
                                        # Save changes if any
                                        if updated:
                                            db_channel.save()
                                            logger.info(f"Updated channel information in database: {db_channel.name} (ID: {db_channel.id})")
                                        
                                    except models.Channel.DoesNotExist:
                                        logger.warning(f"Channel with ID {channel.id} not found in database")
                                    except Exception as e:
                                        logger.error(f"Error updating channel information: {e}")
                                
                                # Run the update function
                                await update_channel_info()
                                
                            except Exception as e:
                                # Ignore errors here as we might already be in the channel
                                if "USER_ALREADY_PARTICIPANT" not in str(e):
                                    logger.debug(f"Could not join channel {identifier}: {e}")
                        except Exception as e:
                            logger.error(f"Could not get entity for channel {identifier}: {e}")
                            continue
                        
                        # Get the category ID for the channel
                        category_id = await get_category_id(channel)
                        
                        # Get messages from the channel
                        messages, channel_entity = await get_channel_messages(client, identifier)
                        
                        if not messages or not channel_entity:
                            logger.warning(f"No messages or channel entity found for {identifier}")
                            continue
                            
                        # Process messages
                        for message in messages:
                            if message.id in last_processed_message_ids.get(identifier, set()):
                                continue  # Skip already processed messages
                                
                            # Save the message
                            await save_message_to_data(
                                message,
                                channel_entity,
                                queue,
                                category_id=category_id,
                                client=client,
                                session=session
                            )
                            
                            # Update last processed message IDs for this channel
                            if identifier not in last_processed_message_ids:
                                last_processed_message_ids[identifier] = set()
                            last_processed_message_ids[identifier].add(message.id)
                            
                    except Exception as e:
                        logger.error(f"Error processing channel {channel.name}: {e}")
                        import traceback
                        logger.error(f"Traceback: {traceback.format_exc()}")
                
                # Sleep between iterations to avoid overloading
                await asyncio.sleep(60)  # Check every 1 minute
                    
            except Exception as e:
                logger.error(f"Error in telethon_task main loop: {e}")
                import traceback
                logger.error(f"Traceback: {traceback.format_exc()}")
                await asyncio.sleep(60)  # Wait a minute before retrying
                
    except Exception as e:
        logger.error(f"Fatal error in telethon_task: {e}")
        import traceback
        logger.error(f"Traceback: {traceback.format_exc()}")
    finally:
        # Clean up clients
        for client_id, client_info in telethon_clients.items():
            if client_info and client_info['client']:
                try:
                    await client_info['client'].disconnect()
                    logger.info(f"Disconnected client {client_id}")
                except Exception as e:
                    logger.error(f"Error disconnecting client {client_id}: {e}")

def handle_interrupt(signum, frame):
    global stop_event
    logger.info("Received signal to stop")
    stop_event = True

def telethon_worker_process(queue, pre_initialized_client=None):
    """
    Entry point for the telethon worker process
    """
    # Set up signal handler
    signal.signal(signal.SIGINT, handle_interrupt)
    signal.signal(signal.SIGTERM, handle_interrupt)
    
    # Configure event loop
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    
    try:
        if pre_initialized_client:
            logger.info("Using pre-initialized client from run.py")
            try:
                # Отримуємо інформацію про сесію без спроби відключення клієнта
                session_name = pre_initialized_client.session.filename
                logger.info(f"Using session file: {session_name}")
            except Exception as e:
                logger.error(f"Error extracting session info from pre-initialized client: {e}")
                session_name = 'telethon_session'
                logger.info(f"Falling back to default session file: {session_name}")
            
            # Запускаємо задачу без pre_initialized_client
            # Це дозволить створити новий клієнт з правильним event loop
            loop.run_until_complete(telethon_task(queue, None))
        else:
            # Run the telethon task normally
            loop.run_until_complete(telethon_task(queue, None))
    except KeyboardInterrupt:
        logger.info("Interrupted")
    except Exception as e:
        logger.error(f"Error in telethon_worker_process: {e}")
        import traceback
        logger.error(f"Traceback: {traceback.format_exc()}")
    finally:
        loop.close()