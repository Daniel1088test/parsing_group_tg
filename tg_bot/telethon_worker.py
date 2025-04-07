import asyncio
import json
import os
import signal
import re
import logging
from datetime import datetime
import django
import sys

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S',
)
logger = logging.getLogger('telegram_parser')

from telethon import TelegramClient, errors, client
from telethon.tl.functions.channels import JoinChannelRequest
from telethon.tl.types import MessageMediaPhoto, MessageMediaDocument, MessageMediaWebPage
from asgiref.sync import sync_to_async

# Try to import API credentials from config, fall back to hardcoded values if needed
try:
    from tg_bot.config import (
        API_ID, API_HASH, FILE_JSON, MAX_MESSAGES,
        CATEGORIES_JSON, DATA_FOLDER, MESSAGES_FOLDER
    )
except ImportError:
    # Fall back to hardcoded values
    logger.warning("Failed to import from config.py, using hardcoded values")
    API_ID = 19840544  # Integer value
    API_HASH = "c839f28bad345082329ec086fca021fa"
    FILE_JSON = 'file.json'
    MAX_MESSAGES = 100000
    DATA_FOLDER = os.path.join(os.path.dirname(__file__), 'data')
    MESSAGES_FOLDER = os.path.join(DATA_FOLDER, 'messages')
    # Create folders if they don't exist
    os.makedirs(DATA_FOLDER, exist_ok=True)
    os.makedirs(MESSAGES_FOLDER, exist_ok=True)

# Configure Django before importing models
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'web_app.settings')
django.setup()

# Now we can import models
from admin_panel import models

def _save_message_to_db(message_data):
    """
    Save message to database
    """
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
    )
    message.save()

def _get_channels():
    channels = list(models.Channel.objects.all().order_by('id'))
    return channels

def _get_category_id(channel):
    category = models.Category.objects.get(channel=channel)
    return category.id 

save_message_to_db = sync_to_async(_save_message_to_db)
get_channels = sync_to_async(_get_channels)
get_category_id = sync_to_async(_get_category_id)

last_processed_message_ids = {}

# Flag for stopping bot
stop_event = False

async def get_channel_messages(client, channel_identifier):
    """
    Receive messages from channel with better error handling for unauthorized sessions
    """
    try:
        # Check if client is authorized
        is_authorized = False
        try:
            is_authorized = await client.is_user_authorized()
        except Exception as e:
            logger.warning(f"Error checking authorization: {e}")
        
        # Extract the username or channel ID from the link
        username = extract_username_from_link(channel_identifier)
        
        if not username:
            logger.warning(f"Could not extract username from link: {channel_identifier}")
            return [], None
            
        # Different approaches based on authorization status
        if is_authorized:
            # Authorized client can use more features
            try:
                # Update dialog cache (skip this for unauthorized sessions)
                await client.get_dialogs()
                
                # Get the channel entity
                channel = await client.get_entity(channel_identifier)
                
                # Get messages
                messages = await client.get_messages(channel, 10)  # Get last 10 messages
                return messages, channel
            except Exception as e:
                logger.error(f"Error with authorized approach: {e}")
                # Fall back to public approach
        
        # For unauthorized clients or if authorized approach failed, try public approach
        try:
            # Try using the direct channel approach
            if isinstance(username, str):
                # Try to get entity directly with username
                try:
                    channel = await client.get_entity(username)
                    messages = await client.get_messages(channel, 10)
                    return messages, channel
                except Exception as e:
                    logger.warning(f"Could not get entity with username {username}: {e}")
            
            # Try using resolved channel ID if available
            normalized_link = await normalize_channel_link(channel_identifier, client)
            if normalized_link != channel_identifier:
                try:
                    # Try with the normalized link
                    logger.info(f"Trying normalized link: {normalized_link}")
                    if 'c/' in normalized_link:
                        # Extract channel ID from the normalized link
                        channel_id = int(re.search(r'c/(\d+)', normalized_link).group(1))
                        from telethon.tl.types import PeerChannel
                        peer = PeerChannel(channel_id)
                        
                        # Try to get messages with the peer
                        messages = await client.get_messages(peer, 10)
                        return messages, None  # We don't have full channel info but have messages
                except Exception as e:
                    logger.warning(f"Error with normalized approach: {e}")
        
            # If all else fails, try some common Telegram API approaches for public channels
            logger.warning(f"Trying alternative approaches for channel: {channel_identifier}")
            
            # Fallback: Try fetching as a public resource
            try:
                from telethon.tl.functions.channels import GetFullChannelRequest
                
                if isinstance(username, str):
                    result = await client(GetFullChannelRequest(channel=username))
                    if result and hasattr(result, 'full_chat'):
                        # We have some channel info, try to get messages now
                        try:
                            messages = await client.get_messages(username, 10)
                            return messages, result.full_chat
                        except:
                            pass
            except Exception as e:
                logger.warning(f"Alternative approach failed: {e}")
                
            logger.error(f"All approaches failed for channel: {channel_identifier}")
            return [], None
                
        except Exception as e:
            logger.error(f"Public channel approach failed: {e}")
            return [], None
            
    except errors.ChannelInvalidError:
        logger.warning(f"Channel {channel_identifier} not found or unavailable.")
        return [], None
    except Exception as e:
        logger.error(f"Error getting messages from channel {channel_identifier}: {e}")
        return [], None

async def download_media(client, message, media_dir):
    """
    Download media from message and return path to file
    """
    try:
        if message.media:
            os.makedirs(media_dir, exist_ok=True)
            timestamp = message.date.strftime("%Y%m%d_%H%M%S")
            file_path = await message.download_media(
                file=os.path.join(media_dir, f"{message.id}_{timestamp}")
            )
            return os.path.basename(file_path) if file_path else None
        return None
    except Exception as e:
        logger.error(f"Error in downloading media: {e}")
        return None

async def save_message_to_data(message, channel, queue, category_id=None, client=None):
    """
    Save message to data folder, with category, and send information to main process.
    """
    try:        
        # Media information
        media_type = None
        media_file = None
        
        # Determine media type and download it
        if message.media and client:  # Check if client is passed
            if isinstance(message.media, MessageMediaPhoto):
                media_type = "photo"
                media_file = await download_media(client, message, "media/messages")
            elif isinstance(message.media, MessageMediaDocument):
                if message.media.document.mime_type.startswith('video'):
                    media_type = "video"
                elif message.media.document.mime_type.startswith('image'):
                    media_type = "gif" if message.media.document.mime_type == 'image/gif' else "image"
                else:
                    media_type = "document"
                media_file = await download_media(client, message, "media/messages")
            elif isinstance(message.media, MessageMediaWebPage):
                media_type = "webpage"
                # Here we don't download webpage, but just specify the type
        
        # Get channel name - avoid accessing DB
        channel_name = getattr(channel, 'name', 'Unknown channel')
        channel_id = getattr(channel, 'id', 0)
        
        # Get message peer ID safely
        peer_id = None
        try:
            if hasattr(message, 'peer_id') and hasattr(message.peer_id, 'channel_id'):
                peer_id = message.peer_id.channel_id
            else:
                peer_id = 0
        except Exception as e:
            logger.error(f"Error getting peer_id: {e}")
            peer_id = 0
            
        # Format the message date
        message_date = None
        try:
            if hasattr(message, 'date'):
                message_date = message.date.strftime("%Y-%m-%d %H:%M:%S")
            else:
                from datetime import datetime
                message_date = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        except Exception as e:
            logger.error(f"Error formatting date: {e}")
            message_date = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        # Save full message without limits
        message_info = {
            'text': message.text,
            'media': "media/messages/" + media_file if media_file else "",
            'media_type': media_type if media_type else None,
            'message_id': message.id,
            'channel_id': peer_id,
            'channel_name': channel_name,
            'link': f"https://t.me/c/{peer_id}/{message.id}",
            'date': message_date
        }
        
        # Save to database using sync_to_async
        try:
            await save_message_to_db(message_info)
            logger.info(f"Saved message from channel {channel_name} (ID: {message.id})")
        except Exception as e:
            logger.error(f"Error saving message to database: {e}")
            import traceback
            logger.error(f"Database error traceback: {traceback.format_exc()}")
        
        # Send message information to main process
        # Don't send channel object, but only necessary data
        queue.put({
            'message_info': message_info, 
            'category_id': category_id
        })
        
        return True

    except Exception as e:
        logger.error(f"Error in saving message to file: {e}")
        import traceback
        logger.error(f"Traceback: {traceback.format_exc()}")
        return False

def extract_username_from_link(link):
    """Extract username/channel from Telegram link"""
    # Match standard t.me links
    username_match = re.search(r'https?://(?:t|telegram)\.me/([^/]+)', link)
    if username_match:
        username = username_match.group(1)
        # Remove any potential plus signs or joinchat prefixes
        if username.startswith('joinchat/'):
            return None  # Joinchat links require different handling
        if username.startswith('+'):
            username = username[1:]
        return username
    
    # Match for channel URLs like https://t.me/c/12345678/123
    channel_match = re.search(r'https?://(?:t|telegram)\.me/c/(\d+)', link)
    if channel_match:
        return int(channel_match.group(1))  # Return channel ID as integer
        
    return None

async def normalize_channel_link(url, client):
    """Normalize channel link to ensure it works with Telethon"""
    if not url:
        return None
        
    # Handle invite links (joinchat)
    if 'joinchat' in url:
        # For private channel invites, we need auth so just return as is
        return url
        
    # Extract username or channel ID
    entity_id = extract_username_from_link(url)
    
    if entity_id:
        if isinstance(entity_id, int):
            # It's already a channel ID
            return f"https://t.me/c/{entity_id}"
        else:
            # Try to get the channel ID if we can
            try:
                entity = await client.get_entity(entity_id)
                if hasattr(entity, 'id'):
                    return f"https://t.me/c/{entity.id}"
            except:
                # Fall back to username-based URL
                return f"https://t.me/{entity_id}"
    
    # If all else fails, return original URL
    return url

async def telethon_task(queue):
    global stop_event, telethon_clients
    """
    background task for parsing messages with Telethon.
    """
    try:
        # Define session files to check for
        session_files = ['telethon_user_session.session', 'telethon_session.session', 'anon.session']
        
        # Check if session files exist, create one if not
        if not any(os.path.exists(file) for file in session_files):
            logger.warning("No session files found. Attempting to create a basic session...")
            try:
                # Create a minimal session file without authentication
                # This won't be fully functional but will allow the app to start
                main_file = 'telethon_session'
                minimal_client = TelegramClient(main_file, API_ID, API_HASH)
                await minimal_client.connect()
                logger.info(f"Created minimal session file: {main_file}.session")
                await minimal_client.disconnect()
                
                # Create copies for other session names
                if os.path.exists(f"{main_file}.session"):
                    for alt_name in [f for f in session_files if f != f"{main_file}.session"]:
                        try:
                            import shutil
                            shutil.copy2(f"{main_file}.session", alt_name)
                            logger.info(f"Created copy of session file as {alt_name}")
                        except Exception as e:
                            logger.error(f"Error creating copy for {alt_name}: {e}")
            except Exception as e:
                logger.error(f"Failed to create basic session file: {e}")
                logger.error("YOU MUST RUN THE AUTHORIZATION PROCESS!")
                logger.error("Use: python -m tg_bot.auth_telethon --force")

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
                logger.error("LIMITED FUNCTIONALITY: The parser will be able to connect but not access private channels.")
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

        # Track parse failures per channel to avoid excessive retries
        channel_failures = {}
        
        # Flag for indicating parse cycle completion
        full_cycle_completed = False

        while not stop_event:
            try:
                channels = await get_channels()
                if not channels:
                    logger.warning("No channels found for parsing. Waiting before retrying...")
                    await asyncio.sleep(30)
                    continue
                
                logger.info(f"Found {len(channels)} channels for parsing")
                
                # Convert all needed attributes to simple values to avoid async access issues
                channels_to_process = []
                
                @sync_to_async
                def prepare_channels_for_async(channels):
                    result = []
                    for channel in channels:
                        if not channel.is_active:
                            continue
                            
                        # Extract all needed attributes to avoid async DB access later
                        channel_data = {
                            'id': channel.id,
                            'name': channel.name,
                            'url': channel.url,
                            'is_active': channel.is_active,
                        }
                        
                        # Add category info if available
                        try:
                            if hasattr(channel, 'category') and channel.category:
                                channel_data['category_id'] = channel.category.id
                                channel_data['category_name'] = channel.category.name
                        except Exception as e:
                            logger.error(f"Error getting category for channel {channel.name}: {e}")
                        
                        # Add session info if available
                        try:
                            if hasattr(channel, 'session') and channel.session:
                                channel_data['session_id'] = channel.session.id
                                channel_data['session_phone'] = channel.session.phone
                        except Exception as e:
                            logger.error(f"Error getting session for channel {channel.name}: {e}")
                            
                        result.append(channel_data)
                    return result
                
                # Get channels data safely
                channels_to_process = await prepare_channels_for_async(channels)
                
                # Calculate active channels
                active_channels = len(channels_to_process)
                logger.info(f"Active channels: {active_channels}/{len(channels)}")
                
                # Debug: Print details of each channel
                for idx, channel_data in enumerate(channels_to_process, 1):
                    session_info = f" [Session: {channel_data.get('session_phone', 'None')}]" if 'session_phone' in channel_data else " [No session]"
                    category_info = f" [Category: {channel_data.get('category_name', 'None')}]" if 'category_name' in channel_data else " [No category]"
                    logger.debug(f"Channel {idx}: {channel_data['name']}{session_info}{category_info} - URL: {channel_data['url']}")
                
                # Track if we've successfully processed any channels
                channels_processed = 0
                
                for channel_data in channels_to_process:
                    # Skip processing if stop_event was triggered
                    if stop_event:
                        break
                    
                    # Get channel data
                    channel_id = channel_data['id']
                    channel_name = channel_data['name']
                    channel_url = channel_data['url']
                    
                    # Skip channels with too many recent failures
                    channel_key = str(channel_id)
                    failure_info = channel_failures.get(channel_key, {'count': 0, 'last_attempt': None})
                    
                    # Skip channels with more than 5 failures until next full cycle
                    if failure_info['count'] >= 5 and full_cycle_completed:
                        # Reset failures count when starting a new cycle
                        if full_cycle_completed:
                            logger.info(f"Resetting failure count for channel '{channel_name}' in new cycle")
                            failure_info['count'] = 0
                        else:
                            logger.warning(f"Skipping channel '{channel_name}' due to {failure_info['count']} previous failures")
                            continue
                        
                    try:
                        # Use channel link
                        channel_link = channel_url
                        
                        # Validate channel URL
                        if not channel_link or not await is_valid_channel_url(channel_link):
                            logger.warning(f"Channel {channel_name} has invalid link: {channel_link}")
                            failure_info['count'] += 1
                            failure_info['last_attempt'] = datetime.now()
                            channel_failures[channel_key] = failure_info
                            continue
                            
                        # Get a client to use - default to the first one if no specific one is set
                        client_key = str(channel_data.get('session_id', 'default')) if 'session_id' in channel_data else 'default'
                        if client_key not in telethon_clients and 'default' in telethon_clients:
                            client_key = 'default'
                            
                        if client_key not in telethon_clients:
                            logger.error(f"No client available for channel {channel_name}")
                            continue
                            
                        client = telethon_clients[client_key]['client']
                        
                        # Check if client is authorized - useful for warnings
                        is_authorized = False
                        try:
                            is_authorized = await client.is_user_authorized()
                            if not is_authorized:
                                logger.warning(f"Processing channel {channel_name} with unauthorized session. Limited functionality expected.")
                        except Exception as e:
                            logger.warning(f"Error checking client authorization: {e}")
                                
                        # First try to join channel if authorized
                        if is_authorized:
                            try:
                                # Extract username from link
                                username = extract_username_from_link(channel_link)
                                if username and isinstance(username, str):
                                    try:
                                        entity = await client.get_entity(username)
                                        await client(JoinChannelRequest(entity))
                                        logger.info(f"Successfully subscribed to channel: {username}")
                                    except Exception as e:
                                        # If we can't join, still continue to get messages
                                        logger.warning(f"Could not join channel {username}: {e}")
                                elif username and isinstance(username, int):
                                    logger.info(f"Direct channel ID provided ({username}), subscription not required")
                                else:
                                    logger.warning(f"Failed to extract valid username from link: {channel_link}")
                            except Exception as e:
                                logger.error(f"Error in subscribing to channel {channel_link}: {e}")
                        else:
                            logger.info(f"Skipping channel subscription for {channel_name} with unauthorized session")

                        # Get messages from channel with more robust approach for unauthorized sessions
                        messages, tg_channel = await get_channel_messages(client, channel_link)
                        
                        if messages and tg_channel:
                            # Check if messages are new
                            latest_message = messages[0]
                            channel_identifier = channel_link  # Use link as identifier
                            last_message_id = last_processed_message_ids.get(channel_identifier)
                            
                            if not last_message_id or latest_message.id > last_message_id:
                                # Get category ID
                                category_id = channel_data.get('category_id')
                                
                                # Create a channel object for save_message_to_data
                                channel_obj = type('ChannelObj', (), {'name': channel_name, 'id': channel_id})
                                
                                # Send message for saving
                                await save_message_to_data(latest_message, channel_obj, queue, category_id, client)
                                last_processed_message_ids[channel_identifier] = latest_message.id
                                channels_processed += 1
                            else:
                                logger.debug(f"Message from channel {channel_name} already processed.")
                        else:
                            logger.warning(f"Failed to get messages from channel: {channel_name}")

                    except errors.FloodError as e:
                        logger.warning(f"Exceeded request frequency limit. Waiting {e.seconds} seconds.")
                        await asyncio.sleep(e.seconds)

                    except Exception as e:
                        logger.error(f"Error in telethon_task for channel {channel_name}: {e}")
                        import traceback
                        logger.error(f"Traceback: {traceback.format_exc()}")

                    # Update failure count
                    failure_info['count'] += 1
                    failure_info['last_attempt'] = datetime.now()
                    channel_failures[channel_key] = failure_info

                # Check if we've completed a full cycle
                if channels_processed > 0:
                    logger.info(f"Successfully processed {channels_processed} channels")
                    full_cycle_completed = (channels_processed == len(channels_to_process))
                else:
                    logger.warning("No channels were processed in this cycle")
                    full_cycle_completed = False

            except Exception as e:
                logger.error(f"Error in reading or processing channels: {e}")
                import traceback
                logger.error(f"Channel processing error traceback: {traceback.format_exc()}")

            await asyncio.sleep(30)  # Pause between checks

    except Exception as e:
        logger.error(f"Error in telethon_task: {e}")
        import traceback
        logger.error(f"Telethon task error traceback: {traceback.format_exc()}")

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
        # Run telethon_task with a timeout to prevent blocking indefinitely
        loop.run_until_complete(asyncio.wait_for(
            telethon_task(queue), 
            timeout=24*60*60  # 24 hour max runtime
        ))
    except asyncio.TimeoutError:
        logger.warning("Telethon task timed out after 24 hours. Restarting...")
        stop_event = True
    except KeyboardInterrupt:
        logger.info("Parser process completed by user (KeyboardInterrupt)")
        stop_event = True
    except EOFError as e:
        # This happens if trying to use input() in a non-interactive environment
        logger.error(f"EOFError: {e} - Cannot use interactive features in this environment")
        logger.error("To use Telethon in this environment, you must provide a pre-authorized session file")
        logger.error("Run 'python create_session_for_railway.py' locally and upload the session file")
        stop_event = True
    except Exception as e:
        logger.error(f"Error in parser process: {e}")
        import traceback
        logger.error(f"Traceback: {traceback.format_exc()}")
        stop_event = True
    finally:
        # Cancel pending tasks
        try:
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
        except Exception as e:
            logger.error(f"Error in cleanup: {e}")
                
        logger.info("Parser process completed")

async def initialize_client(session_id=None, session_filename=None):
    """Initialize a Telethon client for a specific session"""
    logger.info(f"Initializing Telethon client: session_id={session_id}, session_filename={session_filename}")
    
    # If session_id is provided, look up the DB record
    if session_id:
        session = await get_session_by_id(session_id)
        if session and session.session_file:
            session_filename = session.session_file
            # If it's a custom session file from our DB
            if not os.path.exists(f'{session_filename}.session'):
                # Fall back to default session files
                for file in ['telethon_user_session.session', 'telethon_session.session', 'anon.session']:
                    if os.path.exists(file):
                        session_filename = file.replace('.session', '')
                        logger.info(f"Using fallback session file: {session_filename}")
                        break
                else:
                    logger.error(f"No session file found for session ID {session_id}")
                    return None, None
        else:
            # Default session files if the session record doesn't specify one
            for file in ['telethon_user_session.session', 'telethon_session.session', 'anon.session']:
                if os.path.exists(file):
                    session_filename = file.replace('.session', '')
                    logger.info(f"Using default session file: {session_filename}")
                    break
            else:
                logger.error(f"No default session file found")
                return None, None
    elif not session_filename:
        # Default to checking normal session files
        for file in ['telethon_user_session.session', 'telethon_session.session', 'anon.session']:
            if os.path.exists(file):
                session_filename = file.replace('.session', '')
                logger.info(f"Using found session file: {session_filename}")
                break
        else:
            # Create a basic session file if none exists
            logger.warning("No session files found. Creating a basic session file.")
            try:
                session_filename = 'telethon_session'
                # Create a minimal client - just connect, don't try to authorize
                temp_client = TelegramClient(session_filename, API_ID, API_HASH)
                await temp_client.connect()
                logger.info(f"Created basic session file: {session_filename}.session")
                await temp_client.disconnect()
            except Exception as e:
                logger.error(f"Failed to create basic session file: {e}")
                return None, None
    
    # Session file with a unique suffix to avoid conflicts
    process_id = os.getpid()
    unique_session = f"{session_filename}_{session_id or 'default'}_{process_id}"
    logger.debug(f"Using unique session name: {unique_session}")
    
    try:
        # Copy the session file to prevent concurrent access
        if os.path.exists(f'{session_filename}.session'):
            import shutil
            try:
                shutil.copy2(f'{session_filename}.session', f'{unique_session}.session')
                logger.debug(f"Created temporary session file: {unique_session}.session")
            except Exception as e:
                logger.warning(f"Error copying session file: {e} - continuing with original")
                # Continue with original file if copy fails
                unique_session = session_filename
        else:
            logger.warning(f"Session file {session_filename}.session doesn't exist - using name anyway")
            unique_session = session_filename
        
        # Create Telethon client with the session file - handle SSL errors
        try:
            # Check if we're on Windows to add special connection settings
            on_windows = sys.platform.startswith('win')
            connection_params = {}
            
            if on_windows:
                from telethon.network import connection
                connection_params = {
                    'connection': connection.ConnectionTcpFull,
                    'auto_reconnect': True,
                }
            
            client = TelegramClient(
                unique_session, 
                API_ID, 
                API_HASH,
                **connection_params
            )
            logger.info(f"Created Telethon client with session: {unique_session}")
        except ImportError as e:
            if "libssl" in str(e) or "ssl" in str(e):
                logger.warning("SSL library issues detected. Falling back to slower Python encryption.")
                client = TelegramClient(unique_session, API_ID, API_HASH)
            else:
                raise
        
        # Connect with timeout and retry logic - NEVER use client.start() in production!
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
                    logger.info(f"Successfully connected with session: {unique_session}")
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
        
        # Check authorization but don't require it - we'll work in limited mode if not authorized
        authorized = False
        try:
            authorized = await client.is_user_authorized()
        except Exception as e:
            logger.warning(f"Error checking authorization status: {e} - continuing anyway")
        
        if not authorized:
            logger.warning(f"Session {session_filename} is not authorized. Limited functionality available.")
            logger.warning("To authorize: Run 'python -m tg_bot.auth_telethon --force' locally and upload the session file.")
            
        # Get user info if available
        me = None
        try:
            if authorized:
                me = await client.get_me()
                if me:
                    logger.info(f"Initialized client for session {session_filename} as: {me.first_name} (@{me.username}) [ID: {me.id}]")
            
            if not me:
                logger.warning("Could not get user info - running in limited functionality mode")
                # Create a dummy "me" object for operations that need it
                from telethon.tl.types import User
                me = User(
                    id=0,
                    is_self=True,
                    access_hash=0,
                    first_name="Unknown",
                    last_name="User",
                    username="unknown_user"
                )
            
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
            # If we're connected but can't get user info, still return the client with a dummy user
            if connected:
                logger.warning("Returning client without user info for basic operations")
                from telethon.tl.types import User
                dummy_me = User(
                    id=0, 
                    is_self=True,
                    access_hash=0,
                    first_name="Unknown",
                    last_name="User",
                    username="unknown_user"
                )
                return client, dummy_me
            
            await client.disconnect()
            return None, None
            
    except Exception as e:
        logger.error(f"Error initializing client for session {session_filename}: {e}")
        import traceback
        logger.error(f"Traceback: {traceback.format_exc()}")
        try:
            if 'client' in locals() and client:
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

def _get_telegram_sessions():
    """Get all active Telegram sessions from the database"""
    return list(models.TelegramSession.objects.filter(is_active=True).order_by('id'))

def _get_session_by_id(session_id):
    """Get a specific Telegram session by ID"""
    try:
        return models.TelegramSession.objects.get(id=session_id)
    except models.TelegramSession.DoesNotExist:
        return None

# Convert the synchronous DB functions to async
get_telegram_sessions = sync_to_async(_get_telegram_sessions)
get_session_by_id = sync_to_async(_get_session_by_id)

# Global variable to store Telethon clients
telethon_clients = {}

async def is_valid_channel_url(url):
    """Check if a URL is a valid Telegram channel URL"""
    if not url:
        return False
        
    # Check for basic format
    valid_formats = [
        r'https?://(?:t|telegram)\.me/[a-zA-Z0-9_]+',             # Username format
        r'https?://(?:t|telegram)\.me/\+[a-zA-Z0-9_]+',           # + prefix format
        r'https?://(?:t|telegram)\.me/joinchat/[a-zA-Z0-9_-]+',   # Join chat format
        r'https?://(?:t|telegram)\.me/c/\d+(?:/\d+)?',            # Channel ID format
    ]
    
    for pattern in valid_formats:
        if re.match(pattern, url):
            return True
            
    return False