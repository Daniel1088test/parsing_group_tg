from typing import Dict, Any, Callable, Awaitable, Set
from aiogram import BaseMiddleware
from aiogram.types import Message, CallbackQuery, ReplyKeyboardMarkup, KeyboardButton
import logging
from tg_bot.keyboards.main_menu import get_default_keyboard, get_main_menu_keyboard
from asgiref.sync import sync_to_async

logger = logging.getLogger('menu_middleware')

class MenuInitMiddleware(BaseMiddleware):
    """
    Middleware для автоматичної ініціалізації клавіатури меню.
    Гарантує, що користувач завжди має доступ до кнопок меню.
    """
    
    def __init__(self):
        self.users_with_menu: Set[int] = set()
        self.default_keyboard = ReplyKeyboardMarkup(
            keyboard=[
                [KeyboardButton(text="📎 List of channels")],
                [KeyboardButton(text="📍 Categories menu")],
                [KeyboardButton(text="🌐 Go to the site")],
                [KeyboardButton(text="🔑 Add new session")],
            ],
            resize_keyboard=True,
            is_persistent=True,
            input_field_placeholder="Виберіть опцію..."
        )
        logger.info("Menu initialization middleware started")
        logger.info(f"Default keyboard initialized successfully with 4 rows")
    
    async def __call__(
        self,
        handler: Callable[[Message, Dict[str, Any]], Awaitable[Any]],
        event: Message,
        data: Dict[str, Any]
    ) -> Any:
        # Обробляємо тільки повідомлення
        if not isinstance(event, Message):
            return await handler(event, data)
        
        # Отримуємо текст повідомлення
        user_text = event.text if hasattr(event, 'text') and event.text else ''
        logger.info(f"Menu middleware processing message from user {event.from_user.id}: '{user_text}'")
        
        # Спершу викликаємо обробник
        try:
            result = await handler(event, data)
        except Exception as e:
            logger.error(f"Error in handler: {e}")
            # У випадку помилки обробника, просто поверніть базову відповідь
            await event.answer("Відбулася помилка при обробці запиту. Спробуйте знову пізніше або використайте інші команди.")
            return None
        
        # Якщо це не команда /start і не команда /menu, відправляємо клавіатуру
        try:
            if not (user_text.startswith('/start') or user_text.startswith('/menu')):
                # Якщо повідомлення - не одна з кнопок меню, нагадуємо про меню
                menu_texts = ["📎 List of channels", "📍 Categories menu", "🌐 Go to the site", "🔑 Add new session"]
                if user_text not in menu_texts:
                    try:
                        keyboard = self.default_keyboard
                        await event.answer("Доступне меню:", reply_markup=keyboard)
                        logger.info(f"Sent menu to user {event.from_user.id} after handling")
                    except Exception as menu_error:
                        logger.error(f"Error sending menu keyboard: {menu_error}")
        except Exception as e:
            logger.error(f"Error in menu middleware: {e}")
        
        return result 