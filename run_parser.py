#!/usr/bin/env python3
"""
Script to run the Telegram channel parser
"""
import os
import sys
import logging
import traceback
import asyncio
import json
import time
from datetime import datetime, timedelta
import django

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('parser.log', encoding='utf-8'),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger('channel_parser')

# Set up Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
try:
    django.setup()
    logger.info("Django initialized successfully")
except Exception as e:
    logger.error(f"Error initializing Django: {e}")
    logger.error(traceback.format_exc())
    sys.exit(1)

# Import Django models
try:
    from admin_panel.models import Channel, Category, Message, TelegramSession
    from tg_bot.auth_telethon import TelethonClient
    logger.info("Django models imported successfully")
except Exception as e:
    logger.error(f"Error importing Django models: {e}")
    logger.error(traceback.format_exc())
    sys.exit(1)

async def fetch_channels():
    """Fetch active channels from the database"""
    try:
        channels = list(Channel.objects.filter(is_active=True))
        logger.info(f"Found {len(channels)} active channels")
        return channels
    except Exception as e:
        logger.error(f"Error fetching channels: {e}")
        logger.error(traceback.format_exc())
        return []

async def fetch_messages(channel, client):
    """Fetch messages from a channel using the Telethon client"""
    try:
        # Get the channel entity
        entity = await client.get_entity(channel.url)
        if not entity:
            logger.error(f"Could not find entity for channel {channel.name} ({channel.url})")
            return []
        
        # Get last message date from database for incremental updates
        last_message = Message.objects.filter(channel=channel).order_by('-created_at').first()
        
        # Get the messages
        limit = 20  # Reasonable limit for each fetch
        messages = []
        
        if last_message and last_message.created_at:
            # Incremental fetch - get messages after the last one
            offset_date = last_message.created_at
            logger.info(f"Fetching messages from {channel.name} after {offset_date}")
            messages = await client.get_messages(entity, limit=limit, offset_date=offset_date)
        else:
            # Initial fetch - get the latest messages
            logger.info(f"Fetching the latest {limit} messages from {channel.name}")
            messages = await client.get_messages(entity, limit=limit)
        
        logger.info(f"Fetched {len(messages)} messages from {channel.name}")
        return messages
    except Exception as e:
        logger.error(f"Error fetching messages from {channel.name}: {e}")
        logger.error(traceback.format_exc())
        return []

async def save_message(message, channel, session):
    """Save a message to the database"""
    try:
        # Check if message already exists by Telegram ID
        if Message.objects.filter(telegram_message_id=str(message.id), channel=channel).exists():
            logger.debug(f"Message {message.id} already exists, skipping")
            return None
        
        # Extract text, media, and link
        text = message.text or message.message or ''
        media_type = None
        media_file = None
        media_path = None
        
        if message.media:
            media_type = type(message.media).__name__
            # Handle media file if needed
            # This is a simplified version - expand as needed for different media types
        
        # Create the message
        db_message = Message(
            text=text,
            telegram_message_id=str(message.id),
            telegram_channel_id=str(channel.id),
            telegram_link=f"{channel.url}/{message.id}",
            channel=channel,
            session_used=session,
            media_type=media_type
        )
        
        # Save timestamp
        if hasattr(message, 'date') and message.date:
            db_message.created_at = message.date
        
        # Save the message
        db_message.save()
        logger.info(f"Saved message {message.id} from {channel.name}")
        return db_message
    except Exception as e:
        logger.error(f"Error saving message {getattr(message, 'id', 'unknown')}: {e}")
        logger.error(traceback.format_exc())
        return None

async def parse_channel(channel, session):
    """Parse a single channel using a Telegram session"""
    try:
        # Create client
        client = TelethonClient(
            session=session.phone, 
            api_id=session.api_id or os.environ.get('API_ID'),
            api_hash=session.api_hash or os.environ.get('API_HASH')
        )
        
        try:
            # Connect to Telegram
            await client.connect()
            if not await client.is_user_authorized():
                logger.error(f"Session {session.phone} is not authorized, skipping channel {channel.name}")
                return False
            
            # Fetch messages
            messages = await fetch_messages(channel, client)
            
            # Save messages
            for message in messages:
                await save_message(message, channel, session)
            
            logger.info(f"Successfully parsed channel {channel.name}")
            return True
        finally:
            # Always disconnect client
            await client.disconnect()
    except Exception as e:
        logger.error(f"Error parsing channel {channel.name}: {e}")
        logger.error(traceback.format_exc())
        return False

async def main_parser():
    """Main parser function"""
    logger.info("Starting channel parser")
    
    try:
        # Fetch channels to parse
        channels = await fetch_channels()
        if not channels:
            logger.warning("No active channels found")
            return False
        
        # Get available sessions
        try:
            sessions = list(TelegramSession.objects.filter(is_active=True))
            if not sessions:
                logger.error("No active Telegram sessions available")
                return False
            logger.info(f"Found {len(sessions)} active sessions")
        except Exception as e:
            logger.error(f"Error fetching sessions: {e}")
            return False
        
        # Parse each channel with its assigned session
        for channel in channels:
            # Get the session for this channel
            session = None
            if channel.session:
                session = channel.session
            else:
                # If channel has no assigned session, use the first available one
                if sessions:
                    session = sessions[0]
            
            if not session:
                logger.error(f"No suitable session found for channel {channel.name}")
                continue
            
            # Parse the channel
            await parse_channel(channel, session)
        
        logger.info("Channel parsing completed")
        return True
    except Exception as e:
        logger.error(f"Error in main parser: {e}")
        logger.error(traceback.format_exc())
        return False

if __name__ == "__main__":
    try:
        # Run the main parser
        loop = asyncio.get_event_loop()
        success = loop.run_until_complete(main_parser())
        
        # Exit with the appropriate status
        sys.exit(0 if success else 1)
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        logger.error(traceback.format_exc())
        sys.exit(1)