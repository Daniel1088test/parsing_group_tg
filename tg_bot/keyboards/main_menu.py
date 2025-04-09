from aiogram.types import ReplyKeyboardMarkup, KeyboardButton
from asgiref.sync import sync_to_async
import logging

logger = logging.getLogger(__name__)

async def get_main_menu_keyboard():
    """Get the main menu keyboard with the appropriate style"""
    try:
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
                resize_keyboard=True,
                is_persistent=True
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
                resize_keyboard=True,
                is_persistent=True
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
                resize_keyboard=True,
                is_persistent=True
            )
        
        return keyboard
    except Exception as e:
        logger.error(f"Error creating dynamic keyboard: {e}")
        # Return default keyboard if anything fails
        return get_default_keyboard()

def get_default_keyboard():
    """Get a default keyboard that works without any database dependencies"""
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="📎 List of channels")],
            [KeyboardButton(text="📍 Categories menu")],
            [KeyboardButton(text="🌐 Go to the site")],
            [KeyboardButton(text="🔑 Add new session")],
        ],
        resize_keyboard=True,
        is_persistent=True
    )

# Create a default instance for immediate use with persistent flag
main_menu_keyboard = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="📎 List of channels")],
        [KeyboardButton(text="📍 Categories menu")],
        [KeyboardButton(text="🌐 Go to the site")],
        [KeyboardButton(text="🔑 Add new session")],
    ],
    resize_keyboard=True,
    is_persistent=True
)