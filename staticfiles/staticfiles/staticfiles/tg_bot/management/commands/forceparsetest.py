import os
import asyncio
import logging
import traceback
import sys
from django.core.management.base import BaseCommand
from telethon import TelegramClient, errors
from django.utils import timezone
from admin_panel.models import Channel, Message, TelegramSession
from tg_bot.config import API_ID, API_HASH

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler('parser_test.log')
    ]
)
logger = logging.getLogger('force_parser')

class Command(BaseCommand):
    help = 'Force test Telegram parser and save messages directly'
    
    def add_arguments(self, parser):
        parser.add_argument('--limit', type=int, default=10, help='Number of messages to fetch per channel')
        parser.add_argument('--channel', type=str, help='Test specific channel (by name)')
    
    async def parse_channel(self, client, channel, limit=10):
        """Parse one channel and save messages directly to database"""
        self.stdout.write(f"Testing channel: {channel.name} (URL: {channel.url})")
        
        try:
            # Get channel entity
            if channel.url.startswith('https://t.me/'):
                identifier = channel.url
                
                # Extract username or ID from URL
                if '/c/' in channel.url:
                    # Private channel with ID
                    parts = channel.url.split('/c/')
                    if len(parts) > 1 and '/' in parts[1]:
                        channel_id = parts[1].split('/')[0]
                        try:
                            identifier = int(channel_id)
                            self.stdout.write(f"Using channel ID: {identifier}")
                        except ValueError:
                            self.stdout.write(self.style.WARNING(f"Invalid channel ID: {channel_id}"))
                elif channel.url.count('/') == 3:
                    # Public channel with username
                    username = channel.url.split('/')[-1]
                    if username:
                        identifier = username
                        self.stdout.write(f"Using channel username: @{identifier}")
            else:
                self.stdout.write(self.style.ERROR(f"Unsupported channel URL format: {channel.url}"))
                return 0
            
            # Try to get entity
            try:
                entity = await client.get_entity(identifier)
                self.stdout.write(self.style.SUCCESS(f"Successfully got entity: {getattr(entity, 'title', identifier)}"))
            except errors.ChannelPrivateError:
                self.stdout.write(self.style.ERROR(f"Cannot access channel {identifier} - it's private"))
                return 0
            except Exception as e:
                self.stdout.write(self.style.ERROR(f"Error getting entity: {e}"))
                return 0
            
            # Try to join the channel
            try:
                await client.get_dialogs()  # Update dialog cache
                self.stdout.write(f"Attempting to access messages...")
                
                # Get messages
                messages = await client.get_messages(entity, limit=limit)
                self.stdout.write(self.style.SUCCESS(f"Retrieved {len(messages)} messages"))
                
                if not messages:
                    self.stdout.write(self.style.WARNING("No messages found in channel"))
                    return 0
                
                # Process and save each message
                saved_count = 0
                for msg in messages:
                    # Check if this message already exists
                    exists = Message.objects.filter(
                        telegram_message_id=msg.id,
                        channel=channel
                    ).exists()
                    
                    if exists:
                        self.stdout.write(f"Skipping message {msg.id} - already exists")
                        continue
                    
                    # Handle media
                    media_type = None
                    media_path = ""
                    
                    if hasattr(msg, 'media') and msg.media:
                        if hasattr(msg.media, 'photo'):
                            media_type = "photo"
                            # Note: In a real implementation, you'd need to download the media
                            # We're skipping it here to simplify the test
                        elif hasattr(msg.media, 'document'):
                            if msg.media.document.mime_type:
                                if msg.media.document.mime_type.startswith('video'):
                                    media_type = "video"
                                elif msg.media.document.mime_type.startswith('image'):
                                    media_type = "image"
                                else:
                                    media_type = "document"
                    
                    # Create message link
                    message_link = f"https://t.me/c/{entity.id}/{msg.id}" if hasattr(entity, 'id') else ""
                    
                    # Save to database
                    try:
                        new_message = Message(
                            text=msg.text or "",
                            media=media_path,
                            media_type=media_type,
                            telegram_message_id=msg.id,
                            telegram_channel_id=getattr(entity, 'id', None),
                            telegram_link=message_link,
                            channel=channel,
                            created_at=msg.date
                        )
                        new_message.save()
                        saved_count += 1
                        self.stdout.write(self.style.SUCCESS(f"Saved message {msg.id}"))
                    except Exception as e:
                        self.stdout.write(self.style.ERROR(f"Error saving message {msg.id}: {e}"))
                        logger.error(traceback.format_exc())
                
                return saved_count
                
            except Exception as e:
                self.stdout.write(self.style.ERROR(f"Error accessing messages: {e}"))
                logger.error(traceback.format_exc())
                return 0
                
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"Error parsing channel {channel.name}: {e}"))
            logger.error(traceback.format_exc())
            return 0
    
    async def run_parser_test(self, limit=10, specific_channel=None):
        """Run the parser test"""
        # Check if session file exists
        session_file = 'telethon_user_session'
        if not os.path.exists(f'{session_file}.session'):
            self.stdout.write(self.style.ERROR(f"Telethon session file '{session_file}.session' not found."))
            self.stdout.write(self.style.NOTICE("Please run 'python manage.py inittelethon' first to create a session."))
            return False
        
        # Get channels to parse
        if specific_channel:
            channels = Channel.objects.filter(name__icontains=specific_channel, is_active=True)
            if not channels:
                self.stdout.write(self.style.ERROR(f"No active channel found with name containing '{specific_channel}'"))
                return False
        else:
            channels = Channel.objects.filter(is_active=True)
            if not channels:
                self.stdout.write(self.style.ERROR("No active channels found"))
                return False
        
        self.stdout.write(self.style.SUCCESS(f"Found {len(channels)} active channels to test"))
        
        # Initialize Telethon client
        client = TelegramClient(session_file, API_ID, API_HASH)
        
        try:
            await client.connect()
            
            if not await client.is_user_authorized():
                self.stdout.write(self.style.ERROR("Telethon session is not authorized"))
                self.stdout.write(self.style.NOTICE("Please run 'python manage.py inittelethon' to authorize the session"))
                return False
            
            # Get user info
            me = await client.get_me()
            self.stdout.write(self.style.SUCCESS(f"Logged in as: {me.first_name} (@{me.username}, ID: {me.id})"))
            
            # Process each channel
            total_saved = 0
            for channel in channels:
                self.stdout.write(self.style.NOTICE(f"\n===== Testing channel: {channel.name} ====="))
                saved = await self.parse_channel(client, channel, limit)
                total_saved += saved
                self.stdout.write(f"Saved {saved} messages from channel {channel.name}")
            
            self.stdout.write(self.style.SUCCESS(f"\nTotal messages saved: {total_saved}"))
            return total_saved > 0
            
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"Error during parser test: {e}"))
            logger.error(traceback.format_exc())
            return False
        finally:
            await client.disconnect()
    
    def handle(self, *args, **options):
        limit = options['limit']
        specific_channel = options['channel']
        
        self.stdout.write(self.style.NOTICE(f"Starting force parser test (limit: {limit})..."))
        
        # Run the parser test
        success = asyncio.run(self.run_parser_test(limit, specific_channel))
        
        if success:
            self.stdout.write(self.style.SUCCESS("\nParser test completed successfully!"))
            self.stdout.write(self.style.SUCCESS("Messages have been saved to the database."))
            self.stdout.write("You should now see messages on your website.")
        else:
            self.stdout.write(self.style.ERROR("\nParser test failed!"))
            self.stdout.write("Check the logs for more information.")
            
        self.stdout.write("\nTo run the full parser in the background, use:")
        self.stdout.write(self.style.NOTICE("python manage.py runtelethon")) 