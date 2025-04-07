from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, Message
from asgiref.sync import sync_to_async
import re
import logging

logger = logging.getLogger('channels_keyboard')

def get_instructions_kb(website_url):
    """
    Create an inline keyboard with buttons for channel management.
    
    Parameters:
    -----------
    website_url (str): URL of the website
    
    Returns:
    --------
    InlineKeyboardMarkup: Keyboard with channel management buttons
    """
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="➕ Add via web interface", url=f"{website_url}/admin-panel/channel-create/")],
        [InlineKeyboardButton(text="📋 View existing channels", url=f"{website_url}/channels-list/")],
    ])
    
    return keyboard

@sync_to_async
def _check_existing_channel(username=None, channel_id=None):
    """Check if channel already exists in database"""
    from admin_panel.models import Channel
    
    if username:
        return Channel.objects.filter(name__iexact=username).exists()
    elif channel_id:
        return Channel.objects.filter(telegram_id=channel_id).exists()
    return False

@sync_to_async
def _add_channel_to_db(channel_info):
    """Add channel to database"""
    from admin_panel.models import Channel, Category
    
    try:
        # Get or create default category
        default_category, _ = Category.objects.get_or_create(
            name="Uncategorized",
            defaults={'description': 'Default category for channels'}
        )
        
        # Create channel
        channel = Channel(
            name=channel_info.get('name'),
            url=channel_info.get('url'),
            description=channel_info.get('description', ''),
            telegram_id=channel_info.get('channel_id'),
            is_active=True,
            category=default_category
        )
        channel.save()
        
        return channel
    except Exception as e:
        logger.error(f"Error adding channel to DB: {e}")
        return None

async def add_channel_via_message(message: Message, username=None):
    """
    Add a channel from a forwarded message or from username
    """
    channel_info = {}
    
    # If message is forwarded from channel
    if hasattr(message, 'forward_from_chat') and message.forward_from_chat:
        channel = message.forward_from_chat
        
        # Check if we have necessary information
        if not channel.username and not channel.id:
            await message.answer(
                "❌ Could not extract channel information from forwarded message.\n"
                "Make sure the channel is public or try entering the channel link directly."
            )
            return
        
        # Check if channel already exists
        if await _check_existing_channel(username=channel.username, channel_id=channel.id):
            await message.answer(f"Channel '{channel.title}' is already in the database.")
            return
        
        # Prepare channel information
        channel_info = {
            'name': channel.title,
            'url': f"https://t.me/{channel.username}" if channel.username else f"https://t.me/c/{channel.id}",
            'description': f"Added from forwarded message by user {message.from_user.username or message.from_user.id}",
            'channel_id': channel.id
        }
    
    # If username is provided directly
    elif username:
        # Validate username
        if not re.match(r'^[a-zA-Z0-9_]{5,32}$', username):
            await message.answer(
                "❌ Invalid channel username format.\n"
                "Username should be 5-32 characters and contain only letters, numbers, and underscore."
            )
            return
        
        # Check if channel already exists
        if await _check_existing_channel(username=username):
            await message.answer(f"Channel '@{username}' is already in the database.")
            return
        
        # Prepare channel information
        channel_info = {
            'name': username,
            'url': f"https://t.me/{username}",
            'description': f"Added by user {message.from_user.username or message.from_user.id}",
            'channel_id': None  # We don't have channel ID when adding by username
        }
    
    # If we have channel information, add it to the database
    if channel_info:
        channel = await _add_channel_to_db(channel_info)
        
        if channel:
            await message.answer(
                f"✅ Channel '{channel_info['name']}' successfully added to the database.\n"
                "It will be monitored for new messages."
            )
        else:
            await message.answer(
                "❌ Error adding channel to the database.\n"
                "Please try again later or contact administrator."
            )
    else:
        await message.answer(
            "❌ Could not extract channel information.\n"
            "Please forward a message from a channel or use the channel link."
        ) 