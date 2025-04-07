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
        # Try to find channel by exact name
        try:
            channel = models.Channel.objects.get(name=message_data['channel_name'])
        except models.Channel.DoesNotExist:
            # Try to find channel by URL if available and contains a username
            channel_username = None
            if 'link' in message_data:
                channel_username = extract_username_from_link(message_data['link'])
            
            if channel_username:
                # Try to find by URL containing the username
                channels = models.Channel.objects.filter(url__contains=channel_username)
                if channels.exists():
                    channel = channels.first()
                else:
                    # Create new channel with default category
                    default_category, _ = models.Category.objects.get_or_create(name="Uncategorized")
                    channel = models.Channel(
                        name=message_data['channel_name'],
                        url=f"https://t.me/{channel_username}",
                        category=default_category,
                        is_active=True
                    )
                    channel.save()
                    logger.info(f"Created new channel: {channel.name}")
            else:
                # Create new channel as a last resort
                default_category, _ = models.Category.objects.get_or_create(name="Uncategorized")
                channel = models.Channel(
                    name=message_data['channel_name'],
                    url="",  # Empty URL since we don't have one
                    category=default_category,
                    is_active=True
                )
                channel.save()
                logger.info(f"Created new channel: {channel.name}")
        
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
            'media': "media/messages/" + media_file if media_file else "",
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
        # If we have a pre-initialized client, use it
        if pre_initialized_client:
            logger.info("Using pre-initialized client from run.py")
            try:
                me = await pre_initialized_client.get_me()
                telethon_clients['default'] = {
                    'client': pre_initialized_client,
                    'user': me,
                    'session_id': None
                }
                logger.info(f"Using pre-initialized client as: {me.first_name} (@{me.username}) [ID: {me.id}]")
            except Exception as e:
                logger.error(f"Error getting info for pre-initialized client: {e}")
                # Continue below to try initializing from sessions
        
        # If we don't have any clients yet (or pre-init failed), proceed with normal initialization
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
        # Run the telethon task
        loop.run_until_complete(telethon_task(queue, pre_initialized_client))
    except KeyboardInterrupt:
        logger.info("Interrupted")
    except Exception as e:
        logger.error(f"Error in telethon_worker_process: {e}")
        import traceback
        logger.error(f"Traceback: {traceback.format_exc()}")
    finally:
        loop.close()