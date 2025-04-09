from aiogram.types import ReplyKeyboardMarkup, KeyboardButton
import logging

logger = logging.getLogger('main_menu_keyboard')

# Створюємо клавіатуру головного меню - кожна кнопка на окремому рядку
main_menu_keyboard = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="📎 List of channels")],
        [KeyboardButton(text="📍 Categories menu")],
        [KeyboardButton(text="🌐 Go to the site")],
        [KeyboardButton(text="🔑 Add new session")],
    ],
    resize_keyboard=True,
    is_persistent=True,
    input_field_placeholder="Виберіть опцію з меню",
    one_time_keyboard=False,
    selective=False
)

# Функція для створення меню з 4 кнопками
async def get_main_menu_keyboard():
    """
    Створює клавіатуру головного меню з 4 кнопками.
    Ніколи не повертає None - завжди працює.
    """
    try:
        keyboard = ReplyKeyboardMarkup(
            keyboard=[
                [KeyboardButton(text="📎 List of channels")],
                [KeyboardButton(text="📍 Categories menu")],
                [KeyboardButton(text="🌐 Go to the site")],
                [KeyboardButton(text="🔑 Add new session")],
            ],
            resize_keyboard=True,
            is_persistent=True,
            input_field_placeholder="Виберіть опцію з меню"
        )
        logger.info("Generated dynamic main menu keyboard with 4 buttons")
        return keyboard
    except Exception as e:
        logger.error(f"Error generating keyboard: {e}")
        # Запасний варіант
        return get_default_keyboard()

def get_default_keyboard():
    """Створює стандартну клавіатуру без залежностей від бази даних"""
    try:
        keyboard = ReplyKeyboardMarkup(
            keyboard=[
                [KeyboardButton(text="📎 List of channels")],
                [KeyboardButton(text="📍 Categories menu")],
                [KeyboardButton(text="🌐 Go to the site")],
                [KeyboardButton(text="🔑 Add new session")],
            ],
            resize_keyboard=True,
            is_persistent=True,
            input_field_placeholder="Виберіть опцію з меню"
        )
        logger.info("Created fallback keyboard with 4 buttons")
        return keyboard
    except Exception as e:
        logger.error(f"Critical error creating fallback keyboard: {e}")
        # Остаточний запасний варіант - найпростіша версія
        return ReplyKeyboardMarkup(
            keyboard=[
                [KeyboardButton(text="📎 Channels")],
                [KeyboardButton(text="📍 Categories")],
                [KeyboardButton(text="🌐 Site")],
                [KeyboardButton(text="🔑 Session")],
            ],
            resize_keyboard=True,
            is_persistent=True
        )