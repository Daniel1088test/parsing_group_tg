from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton

def get_start_kb(is_admin=False):
    """
    Create main keyboard for bot start command
    
    Args:
        is_admin (bool): Whether the user is an admin
        
    Returns:
        InlineKeyboardMarkup: The keyboard markup
    """
    buttons = []
    
    # Common buttons for all users
    buttons.append([
        InlineKeyboardButton(text="📎 List of channels", callback_data="channels_list")
    ])
    
    buttons.append([
        InlineKeyboardButton(text="📍 Categories", callback_data="categories_list")
    ])
    
    buttons.append([
        InlineKeyboardButton(text="🌐 Go to website", callback_data="go_to_website")
    ])
    
    # Admin-only buttons
    if is_admin:
        buttons.append([
            InlineKeyboardButton(text="➕ Add channel", callback_data="add_channel")
        ])
        
        buttons.append([
            InlineKeyboardButton(text="🔐 Authorize Telethon", callback_data="auth_telethon")
        ])
        
        buttons.append([
            InlineKeyboardButton(text="🔑 Add new session", callback_data="add_session")
        ])
    
    return InlineKeyboardMarkup(inline_keyboard=buttons)

def get_back_button():
    """
    Create back button keyboard
    
    Returns:
        InlineKeyboardMarkup: The keyboard markup with back button
    """
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔙 Back", callback_data="back_to_main")]
    ]) 