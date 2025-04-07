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
        logger.info(f"Saving message to DB: channel '{message_data['channel_name']}', message ID {message_data['message_id']}")
        
        # Try to get the channel
        try:
            channel = models.Channel.objects.get(name=message_data['channel_name'])
        except models.Channel.DoesNotExist:
            logger.error(f"Channel '{message_data['channel_name']}' not found in database")
            return None
        except models.Channel.MultipleObjectsReturned:
            logger.warning(f"Multiple channels found with name '{message_data['channel_name']}'. Using the first one.")
            channel = models.Channel.objects.filter(name=message_data['channel_name']).first()
        
        # Check if message already exists to avoid duplicates
        existing_message = models.Message.objects.filter(
            telegram_message_id=message_data['message_id'],
            telegram_channel_id=message_data['channel_id']
        ).first()
        
        if existing_message:
            logger.debug(f"Message already exists: {message_data['message_id']} from '{message_data['channel_name']}'")
            return existing_message
            
        # Create the message object
        try:
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
            
            session_info = f" (via {message_data.get('session_used').phone})" if message_data.get('session_used') else ""
            logger.info(f"Saved message: channel '{channel.name}', message ID {message_data['message_id']}{session_info}")
            return message
        except Exception as e:
            logger.error(f"Error creating message object: {e}")
            import traceback
            logger.error(f"Traceback: {traceback.format_exc()}")
            return None
            
    except Exception as e:
        logger.error(f"Error saving message: {e}")
        import traceback
        logger.error(f"Traceback: {traceback.format_exc()}")
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
        logger.info(f"Attempting to get messages from: {channel_identifier}")
        
        # Update the dialog cache first to ensure we have the latest channel information
        try:
            await client.get_dialogs(limit=100)
            logger.debug("Successfully updated dialogs cache")
        except Exception as e:
            logger.warning(f"Error updating dialog cache: {e} - continuing anyway")
        
        # Try to get the channel entity - handle different formats
        try:
            # If it's a URL, extract the username or ID first
            if channel_identifier.startswith('http'):
                channel_username = extract_username_from_link(channel_identifier)
                if not channel_username:
                    logger.error(f"Could not extract username from URL: {channel_identifier}")
                    return [], None
                    
                if channel_username.startswith('joinchat/'):
                    # For private invite links, we need to use the full URL
                    logger.info(f"Handling private invite link: {channel_identifier}")
                    channel = await client.get_entity(channel_identifier)
                elif channel_username.isdigit():
                    # For numeric IDs (private channels)
                    logger.info(f"Handling numeric channel ID: {channel_username}")
                    channel = await client.get_entity(int(channel_username))
                else:
                    # For usernames
                    logger.info(f"Handling username: @{channel_username}")
                    channel = await client.get_entity(channel_username)
            else:
                # Direct username or ID
                logger.info(f"Handling direct identifier: {channel_identifier}")
                channel = await client.get_entity(channel_identifier)
                
        except errors.ChannelInvalidError:
            logger.warning(f"Channel {channel_identifier} not found or unavailable. Trying alternative methods...")
            
            # Try different formats if the direct approach fails
            if channel_identifier.startswith('https://t.me/'):
                # Try removing any trailing parts
                base_url = re.sub(r'(/\d+)?$', '', channel_identifier)
                logger.info(f"Trying alternative URL: {base_url}")
                try:
                    channel = await client.get_entity(base_url)
                    logger.info(f"Successfully resolved channel via alternative URL: {base_url}")
                except Exception as e:
                    logger.error(f"Alternative method also failed: {e}")
                    return [], None
            else:
                # No more fallbacks, give up
                logger.error(f"No more fallback methods for: {channel_identifier}")
                return [], None
                
        except Exception as e:
            logger.error(f"Error getting channel entity for {channel_identifier}: {e}")
            import traceback
            logger.error(f"Traceback: {traceback.format_exc()}")
            return [], None
        
        # Get the messages - handle errors and limits
        try:
            # Get messages - make sure we have the channel entity
            if not channel:
                logger.error(f"Channel entity is empty for {channel_identifier}")
                return [], None
                
            channel_title = getattr(channel, 'title', channel_identifier)
            logger.info(f"Getting messages from channel: {channel_title} (ID: {getattr(channel, 'id', 'unknown')})")
            
            # Get the last 10 messages
            messages = await client.get_messages(channel, limit=10)
            if not messages:
                logger.warning(f"No messages found in channel {channel_title}")
                return [], channel
                
            logger.info(f"Retrieved {len(messages)} messages from channel {channel_title}")
            return messages, channel
            
        except errors.ChatAdminRequiredError:
            logger.error(f"Admin rights required to read messages from {getattr(channel, 'title', channel_identifier)}")
            return [], channel
            
        except Exception as e:
            logger.error(f"Error getting messages from channel entity: {e}")
            import traceback
            logger.error(f"Traceback: {traceback.format_exc()}")
            return [], channel
            
    except errors.ChannelInvalidError:
        logger.warning(f"Channel {channel_identifier} not found or unavailable")
        return [], None
        
    except Exception as e:
        logger.error(f"Error getting messages from channel {channel_identifier}: {e}")
        import traceback
        logger.error(f"Traceback: {traceback.format_exc()}")
        return [], None

async def download_media(client, message, media_dir):
    """
    downloading media from the message and returning the path to the file
    """
    try:
        if message.media:
            os.makedirs(media_dir, exist_ok=True)
            timestamp = message.date.strftime("%Y%m%d_%H%M%S")
            file_path = await message.download_media(
                file=os.path.join(media_dir, f"{message.id}_{timestamp}")
            )
            if file_path:
                logger.debug(f"Downloaded media: {os.path.basename(file_path)}")
                return os.path.basename(file_path)
            else:
                logger.warning(f"Unable to download media for message {message.id}")
                return None
        return None
    except Exception as e:
        logger.error(f"Error downloading media: {e}")
        return None

def extract_username_from_link(link):
    """extract username/channel from telegram link"""
    if not link:
        return None
        
    # Handle t.me/username format
    username_match = re.search(r'https?://(?:t|telegram)\.me/([a-zA-Z0-9_]+)(?:/.*)?$', link)
    if username_match:
        return username_match.group(1)
    
    # Handle joinchat links
    joinchat_match = re.search(r'https?://(?:t|telegram)\.me/joinchat/([a-zA-Z0-9_-]+)', link)
    if joinchat_match:
        return 'joinchat/' + joinchat_match.group(1)
    
    # Handle t.me/c/channel_id format (private channels)
    private_match = re.search(r'https?://(?:t|telegram)\.me/c/(\d+)(?:/.*)?$', link)
    if private_match:
        return private_match.group(1)
    
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
        
        # Check if message has a valid channel_id (peer_id can sometimes be None)
        channel_id = None
        if hasattr(message, 'peer_id') and message.peer_id and hasattr(message.peer_id, 'channel_id'):
            channel_id = message.peer_id.channel_id
        elif hasattr(channel, 'id'):
            channel_id = channel.id
        
        # Fallback if we still don't have a channel_id
        if not channel_id and hasattr(channel, 'telegram_id'):
            channel_id = channel.telegram_id
            
        # Create message link
        message_link = ""
        if channel_id:
            # Use username for public channels if available
            if hasattr(channel, 'username') and channel.username:
                message_link = f"https://t.me/{channel.username}/{message.id}"
            else:
                message_link = f"https://t.me/c/{channel_id}/{message.id}"
        
        # save the message
        message_info = {
            'text': message.text or "",  # Handle None case
            'media': "media/messages/" + media_file if media_file else "",
            'media_type': media_type if media_type else None,
            'message_id': message.id,
            'channel_id': channel_id,
            'channel_name': channel_name,
            'link': message_link,
            'date': message.date.strftime("%Y-%m-%d %H:%M:%S"),
            'session_used': session
        }
        
        # save to DB
        saved_message = await save_message_to_db(message_info)
        
        if saved_message:
            # send to queue - FIXING: Changed structure to match what's expected in main.py
            queue.put({
                'message_data': message_info,  # Changed from 'message_info': message_info
                'category_id': category_id
            })
            
            session_info = f" (via {session.phone})" if session else ""
            logger.info(f"Saved message {message.id} from channel '{channel_name}'{session_info}")
        else:
            logger.warning(f"Failed to save message {message.id} from channel '{channel_name}' to database")

    except Exception as e:
        logger.error(f"Error saving message: {e}")
        import traceback
        error_traceback = traceback.format_exc()
        logger.error(f"Error traceback: {error_traceback}")

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
                
                # Debug: Print details of each channel to help troubleshoot
                for idx, channel in enumerate(channels, 1):
                    if channel.is_active:
                        session_info = f" [Session: {channel.session.phone}]" if hasattr(channel, 'session') and channel.session else " [No session]"
                        category_info = f" [Category: {channel.category.name}]" if hasattr(channel, 'category') and channel.category else " [No category]"
                        logger.debug(f"Channel {idx}: {channel.name}{session_info}{category_info} - URL: {channel.url}")
                
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
                            logger.warning(f"Channel '{channel.name}' has no valid link: {channel_link}")
                            continue
                        
                        logger.info(f"Trying to fetch messages from channel '{channel.name}' using link: {channel_link}")
                                
                        # first try to join channel
                        try:
                            # extract username from link
                            username = None
                            if channel_link.startswith('https://t.me/'):
                                # Parse different URL formats
                                if '/joinchat/' in channel_link or '/join/' in channel_link:
                                    # This is an invite link, use it directly
                                    entity = await client.get_entity(channel_link)
                                    logger.info(f"Successfully resolved invite link for channel '{channel.name}'")
                                elif '/c/' in channel_link:
                                    # This is a private channel with a channel ID
                                    match = re.search(r'https?://(?:t|telegram)\.me/c/(\d+)', channel_link)
                                    if match:
                                        channel_id = int(match.group(1))
                                        try:
                                            entity = await client.get_entity(channel_id)
                                            logger.info(f"Successfully resolved private channel ID for '{channel.name}'")
                                        except Exception as e:
                                            logger.error(f"Failed to get entity for channel ID {channel_id}: {e}")
                                            continue
                                    else:
                                        logger.error(f"Could not extract channel ID from link: {channel_link}")
                                        continue
                                else:
                                    # This is a public channel with a username
                                    match = re.search(r'https?://(?:t|telegram)\.me/([a-zA-Z0-9_]+)', channel_link)
                                    if match:
                                        username = match.group(1)
                                        try:
                                            entity = await client.get_entity(username)
                                            logger.info(f"Successfully resolved username @{username} for channel '{channel.name}'")
                                        except Exception as e:
                                            logger.error(f"Failed to get entity for username @{username}: {e}")
                                            continue
                                    else:
                                        logger.error(f"Could not extract username from link: {channel_link}")
                                        continue
                            else:
                                logger.warning(f"Channel link format not supported: {channel_link}")
                                continue
                            
                            # Try to join the channel if we have an entity
                            if 'entity' in locals():
                                try:
                                    await client(JoinChannelRequest(entity))
                                    logger.info(f"Successfully joined channel: {getattr(entity, 'title', username or channel_link)}")
                                except errors.UserAlreadyParticipantError:
                                    logger.debug(f"Already a member of channel: {getattr(entity, 'title', username or channel_link)}")
                                except errors.FloodWaitError as e:
                                    hours, remainder = divmod(e.seconds, 3600)
                                    minutes, seconds = divmod(remainder, 60)
                                    time_str = f"{hours}h {minutes}m {seconds}s" if hours > 0 else f"{minutes}m {seconds}s"
                                    logger.warning(f"Flood wait for {time_str} when joining channel. Skipping.")
                                    continue
                                except Exception as e:
                                    logger.error(f"Error joining channel {channel_link}: {e}")
                        except Exception as e:
                            logger.error(f"Error processing channel link {channel_link}: {e}")

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
                                retry_count += 1
                                if retry_count < max_retries:
                                    await asyncio.sleep(retry_count * 2)
                                
                        if messages and tg_channel:
                            try:
                                logger.info(f"Successfully retrieved {len(messages)} messages from channel '{channel.name}'")
                                
                                # Initialize local variable for last message ID
                                new_last_message_id = None
                                
                                # Check if there are any messages
                                if not messages:
                                    logger.debug(f"No messages found in channel '{channel.name}'")
                                    continue
                                
                                # Create unique identifier for this channel+session combination
                                channel_identifier = f"{channel_link}_{client_info['session_id'] if client_info['session_id'] else 'default'}"
                                
                                # Get the last processed message ID for this channel
                                last_message_id = last_processed_message_ids.get(channel_identifier)
                                
                                # Process messages (newest first)
                                new_messages_count = 0
                                processed_message_ids = set()  # To avoid duplicates in the same run
                                
                                for message in messages:
                                    # Skip if we've already processed this message
                                    if last_message_id and message.id <= last_message_id:
                                        logger.debug(f"Skipping already processed message {message.id} from channel '{channel.name}'")
                                        continue
                                    
                                    # Skip if we've already processed this message in this run
                                    if message.id in processed_message_ids:
                                        logger.debug(f"Skipping duplicate message {message.id} from channel '{channel.name}'")
                                        continue
                                    
                                    processed_message_ids.add(message.id)
                                        
                                    # Update the latest message ID for this channel
                                    if new_last_message_id is None or message.id > new_last_message_id:
                                        new_last_message_id = message.id
                                    
                                    # Get category ID for this channel
                                    category_id = None
                                    if hasattr(channel, 'category_id'):
                                        category_id = await get_category_id(channel)
                                    
                                    # Process message
                                    session_info = f" (via {session.phone})" if session else ""
                                    logger.info(f"New message in channel '{channel.name}' [ID: {message.id}]{session_info}")
                                    
                                    # Save message data
                                    await save_message_to_data(message, channel, queue, category_id, client, session)
                                    new_messages_count += 1
                                    
                                    # Limit the number of new messages to process at once (to avoid flooding)
                                    if new_messages_count >= 5:  # Process max 5 new messages at once
                                        logger.info(f"Reached limit of new messages to process at once for channel '{channel.name}'")
                                        break
                                    
                                # Update the last processed message ID for this channel
                                if new_last_message_id:
                                    last_processed_message_ids[channel_identifier] = new_last_message_id
                                    logger.debug(f"Updated last processed message ID for channel '{channel.name}' to {new_last_message_id}")
                                    
                                if new_messages_count > 0:
                                    logger.info(f"Processed {new_messages_count} new messages from channel '{channel.name}'")
                                else:
                                    logger.debug(f"No new messages from channel '{channel.name}'")
                                
                            except Exception as e:
                                logger.error(f"Error processing messages from channel '{channel.name}': {e}")
                                import traceback
                                logger.error(f"Traceback: {traceback.format_exc()}")
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
                        import traceback
                        logger.error(f"Traceback: {traceback.format_exc()}")

                    # Small sleep between processing channels to avoid rate limiting
                    await asyncio.sleep(5)
                    
                # End of channels loop
                if stop_event:
                    break
                    
                logger.info("Parsing cycle completed. Waiting 30 seconds for the next cycle...")
                await asyncio.sleep(30)  # pause between checks
                
            except Exception as e:
                logger.error(f"Error reading or processing channels: {e}")
                import traceback
                logger.error(f"Traceback: {traceback.format_exc()}")
                await asyncio.sleep(30)  # Wait before retrying
                
    except Exception as e:
        logger.error(f"Error in telethon_task: {e}")
        import traceback
        logger.error(f"Traceback: {traceback.format_exc()}")
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
        import traceback
        logger.error(f"Traceback: {traceback.format_exc()}")
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