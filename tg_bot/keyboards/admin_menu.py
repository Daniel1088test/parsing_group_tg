from aiogram.types import ReplyKeyboardMarkup, KeyboardButton

admin_menu_keyboard = ReplyKeyboardMarkup(
    keyboard=[
        [
            KeyboardButton(text="📎 List of channels"),
            KeyboardButton(text="📍 Categories menu")
        ],
        [
            KeyboardButton(text="🌐 Site"),
            KeyboardButton(text="❓ Help")
        ],
        [
            KeyboardButton(text="ℹ️ Information"),
            KeyboardButton(text="👨‍💻 Support")
        ]
    ],
    resize_keyboard=True,
    input_field_placeholder="Select an option..."
) 