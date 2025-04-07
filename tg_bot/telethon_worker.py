import asyncio
import json
import os
import signal
import re
import logging
from datetime import datetime
import django
from typing import Dict, Optional, Tuple
import base64

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
        import traceback
        error_traceback = traceback.format_exc()
        logger.error(f"Error traceback: {error_traceback}")

def extract_username_from_link(link):
    """extract username/channel from telegram link"""
    username_match = re.search(r'https?://(?:t|telegram)\.me/([^/]+)', link)
    if username_match:
        return username_match.group(1)
    return None

async def initialize_client(session):
    """Initialize a Telethon client with the session from database"""
    try:
        if session.session_string:
            # Create client with saved session string
            client = TelegramClient(
                StringSession(base64.b64decode(session.session_string).decode()),
                session.api_id,
                session.api_hash
            )
        else:
            # Fallback to file-based session if no string session
            client = TelegramClient('telethon_session', session.api_id, session.api_hash)
            
        await client.connect()
        
        if not await client.is_user_authorized():
            logger.error(f"Session {session.phone} exists but is not authorized")
            await client.disconnect()
            return None
            
        return client
    except Exception as e:
        logger.error(f"Error initializing client for session {session.phone}: {e}")
        return None

async def telethon_task(queue):
    """Main Telethon task"""
    try:
        # Get active sessions from database
        sessions = await get_telegram_sessions()
        if not sessions:
            logger.warning("No active Telegram sessions found in the database")
            return
            
        # Try to initialize clients for all sessions
        clients = []
        for session in sessions:
            client = await initialize_client(session)
            if client:
                clients.append((client, session))
                
        if not clients:
            logger.error("Failed to initialize any clients. Parser cannot run.")
            return
            
        logger.info(f"Successfully initialized {len(clients)} clients")
        
        while not stop_event:
            try:
                # Get all channels from database
                channels = await get_channels()
                
                for channel in channels:
                    # Skip inactive channels
                    if not channel.is_active:
                        continue
                        
                    # Get category ID for the channel
                    category_id = await get_category_id(channel)
                    if not category_id:
                        continue
                        
                    # Choose a client for this channel
                    client, session = clients[0]  # You can implement more sophisticated client selection
                    
                    # Get and process messages
                    messages, channel_entity = await get_channel_messages(client, channel.url)
                    
                    for message in messages:
                        # Skip if we've already processed this message
                        if message.id in last_processed_message_ids.get(channel.id, set()):
                            continue
                            
                        # Save message and add to queue
                        await save_message_to_data(message, channel_entity, queue, category_id, client, session)
                        
                        # Update processed messages set
                        if channel.id not in last_processed_message_ids:
                            last_processed_message_ids[channel.id] = set()
                        last_processed_message_ids[channel.id].add(message.id)
                        
                # Sleep before next iteration
                await asyncio.sleep(60)
                
            except Exception as e:
                logger.error(f"Error in main loop: {e}")
                await asyncio.sleep(60)
                
    except Exception as e:
        logger.error(f"Fatal error in telethon task: {e}")
    finally:
        # Disconnect all clients
        for client, _ in clients:
            try:
                await client.disconnect()
            except:
                pass

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