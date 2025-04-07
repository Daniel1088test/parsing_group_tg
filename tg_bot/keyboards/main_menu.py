from aiogram.types import ReplyKeyboardMarkup, KeyboardButton
from aiogram.utils.keyboard import ReplyKeyboardBuilder

async def main_menu_keyboard(is_admin: bool = False) -> ReplyKeyboardMarkup:
    """Create main menu keyboard based on user role"""
    builder = ReplyKeyboardBuilder()
    
    # Add session management button for all users
    builder.add(KeyboardButton(text="🔑 Authorize Session"))
    
    if is_admin:
        # Admin-only buttons
        builder.add(KeyboardButton(text="📎 List of channels"))
        builder.add(KeyboardButton(text="📋 Categories menu"))
        builder.add(KeyboardButton(text="🌐 Go to the site"))
    
    # Adjust to 2 buttons per row
    builder.adjust(2)
    
    return builder.as_markup(resize_keyboard=True)