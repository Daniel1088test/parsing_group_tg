from aiogram import Router, F, types
from aiogram.filters import Command
from tg_bot.keyboards.main_menu import main_menu_keyboard, get_main_menu_keyboard
from tg_bot.keyboards.session_menu import session_menu_keyboard
from admin_panel.models import Channel, Category, TelegramSession, BotSettings
from asgiref.sync import sync_to_async
import logging

# Створюємо роутер
menu_buttons_router = Router()
logger = logging.getLogger('telegram_bot')

@menu_buttons_router.message(F.text.startswith("📎"))
async def handle_channels_button(message: types.Message):
    """Обробник для кнопок з каналами (варіанти меню)"""
    # Перенаправляємо на стандартний хендлер каналів
    from tg_bot.handlers.common import list_channels
    await list_channels(message)

@menu_buttons_router.message(F.text.startswith("📍"))
async def handle_categories_button(message: types.Message):
    """Обробник для кнопок з категоріями (варіанти меню)"""
    # Перенаправляємо на стандартний хендлер категорій
    from tg_bot.handlers.common import list_categories
    await list_categories(message)

@menu_buttons_router.message(F.text.startswith("🌐"))
async def handle_website_button(message: types.Message):
    """Обробник для кнопок з посиланням на сайт (варіанти меню)"""
    # Перенаправляємо на стандартний хендлер сайту
    from tg_bot.handlers.common import goto_website
    await goto_website(message)

@menu_buttons_router.message(F.text.startswith("🔑") | F.text.startswith("➕"))
async def handle_add_session_button(message: types.Message):
    """Обробник для кнопок з додаванням сесій (варіанти меню)"""
    try:
        await message.answer(
            "Select an action:",
            reply_markup=session_menu_keyboard
        )
    except Exception as e:
        logger.error(f"Error in handle_add_session_button: {e}")
        await message.answer("An error occurred. Please try again later.")

# Обробники для інших варіантів тексту кнопок
@menu_buttons_router.message(F.text.contains("session") | F.text.contains("Session"))
async def handle_session_text(message: types.Message):
    """Обробник для текстових запитів з сесіями"""
    try:
        await message.answer(
            "Select an action for session management:",
            reply_markup=session_menu_keyboard
        )
    except Exception as e:
        logger.error(f"Error in handle_session_text: {e}")
        await message.answer("An error occurred. Please try again later.")

@menu_buttons_router.message(F.text.contains("channel") | F.text.contains("Channel"))
async def handle_channel_text(message: types.Message):
    """Обробник для текстових запитів з каналами"""
    # Перенаправляємо на стандартний хендлер каналів
    from tg_bot.handlers.common import list_channels
    await list_channels(message)

@menu_buttons_router.message(F.text.contains("category") | F.text.contains("Category"))
async def handle_category_text(message: types.Message):
    """Обробник для текстових запитів з категоріями"""
    # Перенаправляємо на стандартний хендлер категорій
    from tg_bot.handlers.common import list_categories
    await list_categories(message)

@menu_buttons_router.message(F.text.contains("website") | F.text.contains("site") | F.text.contains("Site"))
async def handle_site_text(message: types.Message):
    """Обробник для текстових запитів з сайтом"""
    # Перенаправляємо на стандартний хендлер сайту
    from tg_bot.handlers.common import goto_website
    await goto_website(message) 