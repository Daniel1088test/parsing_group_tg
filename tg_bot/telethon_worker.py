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

# import models
from admin_panel import models

def _save_message_to_db(message_data):
    """
    save message to db
    """
    try:
        channel = models.Channel.objects.get(name=message_data['channel_name'])
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
                await asyncio.sleep(30)  # Wait before retrying
                
    except Exception as e:
        logger.error(f"Error in telethon_task: {e}")
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