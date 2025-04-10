from aiogram.types import ReplyKeyboardMarkup, KeyboardButton

# Admin menu keyboard
admin_menu_keyboard = ReplyKeyboardMarkup(keyboard=[
    [KeyboardButton(text="📝 Add Channel"), KeyboardButton(text="📋 List of channels")],
    [KeyboardButton(text="🔐 Authorize Telethon"), KeyboardButton(text="⚙️ Settings")],
    [KeyboardButton(text="🌐 Site"), KeyboardButton(text="🔙 Back to main menu")]
], resize_keyboard=True) 