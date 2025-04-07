from aiogram.types import ReplyKeyboardMarkup, KeyboardButton

main_menu_keyboard = ReplyKeyboardMarkup(
    keyboard=[
        [
            KeyboardButton(text="📎 List of channels"),
        ],
        [
            KeyboardButton(text="📍 Categories menu"),
        ],
        [
            KeyboardButton(text="🌐 Go to the site")
        ],
        [
            KeyboardButton(text="🔑 Add new session")
        ]
    ],
    resize_keyboard=True,
    one_time_keyboard=False,
    input_field_placeholder="Select an option from the menu..."
)