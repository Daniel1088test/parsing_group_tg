import asyncio
import json
import os
import signal
import re
import logging
from datetime import datetime
import django
from typing import Dict, Optional, Tuple
from django.utils import timezone

from telethon import TelegramClient, errors, client, events
from telethon.tl.functions.channels import JoinChannelRequest
from telethon.tl.types import MessageMediaPhoto, MessageMediaDocument, MessageMediaWebPage
from asgiref.sync import sync_to_async
from tg_bot.config import (
    API_ID, API_HASH, FILE_JSON, MAX_MESSAGES,
    CATEGORIES_JSON, DATA_FOLDER, MESSAGES_FOLDER
)
from tg_bot.session_manager import create_client_from_session

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
from admin_panel.models import Channel, Message, Category, TelegramSession

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
                channel = models.Channel.objects.get(name=channel_name)
                logger.info(f"Found channel by exact name: {channel.name} (ID: {channel.id})")
            except models.Channel.DoesNotExist:
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
                channel.save()
                logger.info(f"Created new channel: {channel.name} (ID: {channel.id})")
        
        # Parse the date string to datetime
        message_date = datetime.strptime(message_data['date'], "%Y-%m-%d %H:%M:%S")
        message_date = timezone.make_aware(message_date)
        
        # Create message with new fields structure
        message = models.Message(
            channel=channel,
            message_id=message_data['message_id'],
            date=message_date,
            text=message_data['text'],
            has_image=message_data.get('media_type') == 'photo',
            has_video=message_data.get('media_type') == 'video',
            has_audio=message_data.get('media_type') == 'audio',
            has_document=message_data.get('media_type') == 'document',
            session_used=message_data.get('session_used')
        )
        message.save()
        
        # Log message saving
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
        # determine the type of media
        media_type = None
        has_image = False
        has_video = False
        has_audio = False
        has_document = False
        
        # determine the type of media
        if message.media and client:
            if isinstance(message.media, MessageMediaPhoto):
                media_type = "photo"
                has_image = True
            elif isinstance(message.media, MessageMediaDocument):
                if message.media.document.mime_type.startswith('video'):
                    media_type = "video"
                    has_video = True
                elif message.media.document.mime_type.startswith('audio'):
                    media_type = "audio"
                    has_audio = True
                else:
                    media_type = "document"
                    has_document = True
            elif isinstance(message.media, MessageMediaWebPage):
                media_type = "webpage"
        
        # get the channel name
        channel_name = getattr(channel, 'title', None) or getattr(channel, 'name', 'Unknown channel')
        
        # prepare message info
        message_info = {
            'text': message.text or '',
            'message_id': message.id,
            'channel_id': message.peer_id.channel_id,
            'channel_name': channel_name,
            'date': message.date,
            'has_image': has_image,
            'has_video': has_video,
            'has_audio': has_audio,
            'has_document': has_document,
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

async def initialize_client(session: TelegramSession) -> Optional[TelegramClient]:
    """
    Initialize Telethon client for a session
    """
    try:
        if not session.session_data:
            logger.error(f"No session data for session {session.id}")
            return None
            
        client = await create_client_from_session(
            api_id=API_ID,
            api_hash=API_HASH,
            session_data=session.session_data
        )
        
        if client:
            logger.info(f"Successfully initialized client for session {session.id}")
            return client
        else:
            logger.error(f"Failed to initialize client for session {session.id}")
            return None
            
    except Exception as e:
        logger.error(f"Error initializing client for session {session.id}: {e}")
        return None

async def telethon_task():
    """
    Main task for Telethon client
    """
    global stop_event
    
    while not stop_event:
        try:
            # Get active sessions
            sessions = await get_telegram_sessions()
            if not sessions:
                logger.warning("No active Telegram sessions found")
                await asyncio.sleep(60)
                continue
                
            # Initialize clients for each session
            for session in sessions:
                if session.id not in telethon_clients:
                    client = await initialize_client(session)
                    if client:
                        telethon_clients[session.id] = client
                        
            if not telethon_clients:
                logger.error("No Telethon clients could be initialized")
                await asyncio.sleep(60)
                continue
                
            # Get channels to parse
            channels = await get_channels()
            if not channels:
                logger.warning("No channels to parse")
                await asyncio.sleep(60)
                continue
                
            # Process each channel
            for channel in channels:
                if not channel.is_active:
                    continue
                    
                # Get session for this channel
                session = await get_session_by_id(channel.session_id if hasattr(channel, 'session_id') else None)
                if not session:
                    logger.warning(f"No session found for channel {channel.name}")
                    continue
                    
                # Get client for this session
                client = telethon_clients.get(session.id)
                if not client:
                    logger.warning(f"No client found for session {session.id}")
                    continue
                    
                try:
                    # Get messages from channel
                    messages, channel_entity = await get_channel_messages(client, channel.url)
                    if not messages:
                        continue
                        
                    # Process messages
                    for message in messages:
                        if not message or not message.id:
                            continue
                            
                        # Skip if already processed
                        if message.id in last_processed_message_ids.get(channel.id, set()):
                            continue
                            
                        # Process message
                        message_data = {
                            'channel_name': channel.name,
                            'channel_id': channel.id,
                            'message_id': message.id,
                            'date': message.date.strftime("%Y-%m-%d %H:%M:%S"),
                            'text': message.text or '',
                            'link': channel.url,
                            'session_used': session
                        }
                        
                        # Determine media type
                        if message.media:
                            if isinstance(message.media, MessageMediaPhoto):
                                message_data['media_type'] = 'photo'
                            elif isinstance(message.media, MessageMediaDocument):
                                if message.media.document.mime_type.startswith('video'):
                                    message_data['media_type'] = 'video'
                                elif message.media.document.mime_type.startswith('audio'):
                                    message_data['media_type'] = 'audio'
                                else:
                                    message_data['media_type'] = 'document'
                                    
                        # Save message
                        saved_message = await save_message_to_db(message_data)
                        if saved_message:
                            # Update last processed messages
                            if channel.id not in last_processed_message_ids:
                                last_processed_message_ids[channel.id] = set()
                            last_processed_message_ids[channel.id].add(message.id)
                            
                except Exception as e:
                    logger.error(f"Error processing channel {channel.name}: {e}")
                    continue
                    
            # Sleep before next iteration
            await asyncio.sleep(60)
            
        except Exception as e:
            logger.error(f"Error in telethon_task: {e}")
            await asyncio.sleep(60)
            
    # Disconnect all clients when stopping
    for client in telethon_clients.values():
        try:
            await client.disconnect()
        except:
            pass
    telethon_clients.clear()

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
            loop.run_until_complete(telethon_task())
        else:
            # Run the telethon task normally
            loop.run_until_complete(telethon_task())
    except KeyboardInterrupt:
        logger.info("Interrupted")
    except Exception as e:
        logger.error(f"Error in telethon_worker_process: {e}")
        import traceback
        logger.error(f"Traceback: {traceback.format_exc()}")
    finally:
            loop.close()

async def process_message(event, channel_db):
    """Process and save a new message"""
    try:
        # Get the message
        message = event.message
        
        # Extract message info
        message_info = {
            'message_id': message.id,
            'date': timezone.make_aware(message.date),
            'text': message.text if message.text else '',
            'channel_id': channel_db.id,
        }
        
        # Handle media
        if message.media:
            if hasattr(message.media, 'photo'):
                message_info['has_image'] = True
            if hasattr(message.media, 'document'):
                message_info['has_document'] = True
                if hasattr(message.media.document, 'mime_type'):
                    if message.media.document.mime_type.startswith('video'):
                        message_info['has_video'] = True
                    elif message.media.document.mime_type.startswith('audio'):
                        message_info['has_audio'] = True
        
        # Save message to database
        @sync_to_async
        def save_message():
            try:
                Message.objects.create(**message_info)
                logger.info(f"Saved message {message.id} from channel {channel_db.name}")
            except Exception as e:
                logger.error(f"Error saving message: {e}")

        await save_message()
        
    except Exception as e:
        logger.error(f"Error processing message: {e}")