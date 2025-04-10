from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
import logging

logger = logging.getLogger('keyboards')

def format_session_info(session, compact=True):
    """
    Format session information for display
    
    Args:
        session: TelegramSession object or None
        compact: If True, returns a short emoji indicator, otherwise returns a descriptive text
    
    Returns:
        str: Formatted session information
    """
    # Safety check - don't try to access session if it's not properly loaded
    # This prevents triggering additional DB queries in async contexts
    if session is None or not hasattr(session, 'phone'):
        return "" if compact else "No session"
    
    if compact:
        return f"🔑" # Key emoji for sessions
    else:
        return f"Session: {session.phone}"

def get_channels_keyboard(channels, category_id=None):
    """
    create a keyboard with a list of channels. 
    If category_id is specified, filter the channels by category.
    
    Args:
        channels: list of Channel objects or a dictionary of channel data
        category_id: category ID for filtering (optional)
    """
    keyboard = []
    
    # check the format of the channel data
    if not channels:
        logger.debug("Empty list of channels when creating the keyboard")
    elif isinstance(channels, dict):
        # processing data in dictionary format (from channels_data)
        logger.debug(f"Processing {len(channels)} channels from the dictionary")
        for channel_id, data in channels.items():
            channel_category = data.get('category', None)
            
            # filter by category if specified
            if category_id is None or channel_category == str(category_id):
                status = "✅" if data.get('Work') == "True" else "❌"
                session_indicator = format_session_info(data.get('session', None))
                button_text = f"{status} {data.get('Group_Name', 'Unknown')} {session_indicator}"
                keyboard.append([
                    InlineKeyboardButton(text=button_text, callback_data=f"channel_{channel_id}"),
                    InlineKeyboardButton(text="✏️", callback_data=f"edit_channel_{channel_id}")
                ])
    else:
        # processing data in list of objects format (from the database)
        logger.debug(f"Processing {len(channels)} channels from the list of objects")
        for channel in channels:
            channel_category_id = getattr(channel, 'category_id', None)
            
            # filter by category if specified
            if category_id is None or str(channel_category_id) == str(category_id):
                status = "✅" if channel.is_active else "❌"
                
                # Safely get session information without triggering DB queries
                if hasattr(channel, '_prefetched_objects_cache') and 'session' in channel._prefetched_objects_cache:
                    session = channel._prefetched_objects_cache.get('session')
                elif hasattr(channel, '_state') and hasattr(channel._state, 'fields_cache') and 'session' in channel._state.fields_cache:
                    session = channel._state.fields_cache.get('session')
                else:
                    # No session preloaded, don't try to access it
                    session = None
                
                session_indicator = format_session_info(session)
                button_text = f"{status} {channel.name} {session_indicator}"
                keyboard.append([
                    InlineKeyboardButton(text=button_text, callback_data=f"channel_{channel.id}"),
                    InlineKeyboardButton(text="✏️", callback_data=f"edit_channel_{channel.id}")
                ])

    # add buttons for adding and removing channels
    keyboard.append([InlineKeyboardButton(text="➕ Add channel", callback_data="add_channel")])
    keyboard.append([InlineKeyboardButton(text="➖ Remove channel", callback_data="remove_channel")])

    if category_id:
        # "Back" button to return to the list of categories
        keyboard.append([InlineKeyboardButton(text="⬅️ Back", callback_data="back")])

    return InlineKeyboardMarkup(inline_keyboard=keyboard)

def get_categories_keyboard(channels_data, categories):
    """
    create a keyboard with a list of categories based on data from categories.json
    """
    keyboard = []
    
    # Make sure categories are sorted by ID
    if categories:
        categories = sorted(categories, key=lambda x: x.id)
        for category in categories:
            # Safely get session information without triggering DB queries
            if hasattr(category, '_prefetched_objects_cache') and 'session' in category._prefetched_objects_cache:
                session = category._prefetched_objects_cache.get('session')
            elif hasattr(category, '_state') and hasattr(category._state, 'fields_cache') and 'session' in category._state.fields_cache:
                session = category._state.fields_cache.get('session')
            else:
                # No session preloaded, don't try to access it
                session = None
                
            session_indicator = format_session_info(session)
            keyboard.append([
                InlineKeyboardButton(text=f"{category.name} {session_indicator}", callback_data=f"category_{category.id}"),
                InlineKeyboardButton(text="✏️", callback_data=f"edit_category_{category.id}")
            ])
    
    # add buttons for adding and removing categories
    keyboard.append([InlineKeyboardButton(text="➕ Add category", callback_data="add_category")])
    keyboard.append([InlineKeyboardButton(text="➖ Remove category", callback_data="remove_category")])

    return InlineKeyboardMarkup(inline_keyboard=keyboard)

def get_back_button():
    """
    create a "Back" button
    """
    return InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="⬅️ Back", callback_data="back")]])