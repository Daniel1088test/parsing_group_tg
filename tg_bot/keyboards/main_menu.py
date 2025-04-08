from aiogram.types import ReplyKeyboardMarkup, KeyboardButton
from asgiref.sync import sync_to_async

async def get_main_menu_keyboard():
    """Get the main menu keyboard with the appropriate style"""
    # Get bot settings
    from admin_panel.models import BotSettings
    settings = await sync_to_async(BotSettings.get_settings)()
    
    # Choose keyboard style based on settings
    style = settings.menu_style if hasattr(settings, 'menu_style') else 'default'
    
    if style == 'compact':
        # Compact style - more buttons per row
        keyboard = ReplyKeyboardMarkup(
            keyboard=[
                [
                    KeyboardButton(text="📎 List of channels"),
                    KeyboardButton(text="📍 Categories menu"),
                ],
                [
                    KeyboardButton(text="🌐 Go to the site"),
                    KeyboardButton(text="🔑 Add new session"),
                ]
            ],
            resize_keyboard=True
        )
    elif style == 'expanded':
        # Expanded style - descriptive buttons
        keyboard = ReplyKeyboardMarkup(
            keyboard=[
                [KeyboardButton(text="📎 View all channels")],
                [KeyboardButton(text="📍 Browse channel categories")],
                [KeyboardButton(text="🌐 Open web interface")],
                [KeyboardButton(text="🔑 Authorize new session")],
            ],
            resize_keyboard=True
        )
    else:
        # Default style
        keyboard = ReplyKeyboardMarkup(
            keyboard=[
                [KeyboardButton(text="📎 List of channels")],
                [KeyboardButton(text="📍 Categories menu")],
                [KeyboardButton(text="🌐 Go to the site")],
                [KeyboardButton(text="🔑 Add new session")],
            ],
            resize_keyboard=True
        )
    
    return keyboard

# Create a default instance for immediate use
main_menu_keyboard = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="📎 List of channels")],
        [KeyboardButton(text="📍 Categories menu")],
        [KeyboardButton(text="🌐 Go to the site")],
        [KeyboardButton(text="🔑 Add new session")],
    ],
    resize_keyboard=True
)