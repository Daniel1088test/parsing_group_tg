from typing import Dict, Any, Callable, Awaitable
from aiogram import BaseMiddleware
from aiogram.types import Message, CallbackQuery
import logging
from tg_bot.keyboards.main_menu import get_default_keyboard

logger = logging.getLogger('menu_middleware')

class MenuInitMiddleware(BaseMiddleware):
    """Middleware to ensure users always have a menu visible"""
    
    def __init__(self):
        self.user_states = {}  # Store user interaction states
        logger.info("Menu initialization middleware started")
    
    async def __call__(
        self,
        handler: Callable[[Message, Dict[str, Any]], Awaitable[Any]],
        event: Message | CallbackQuery,
        data: Dict[str, Any]
    ) -> Any:
        # First call the handler to process the event
        result = await handler(event, data)
        
        # For message events, check if we need to show the menu
        if isinstance(event, Message) and event.text:
            user_id = event.from_user.id
            
            # Skip command messages
            if event.text.startswith('/'):
                return result
                
            # Skip messages with specific text like menu buttons
            menu_buttons = ["📎 List of channels", "📍 Categories menu", 
                            "🌐 Go to the site", "🔑 Add new session"]
            if event.text in menu_buttons:
                return result
            
            # Check if this is the first time we're seeing this user
            if user_id not in self.user_states:
                self.user_states[user_id] = {
                    'menu_shown': False,
                    'message_count': 0
                }
            
            # Increment message count for this user
            self.user_states[user_id]['message_count'] += 1
            
            # If user has sent more than 2 messages and never seen the menu, show it
            if (self.user_states[user_id]['message_count'] >= 2 and 
                not self.user_states[user_id]['menu_shown']):
                try:
                    keyboard = get_default_keyboard()
                    await event.answer(
                        "Here's the menu to help you navigate:",
                        reply_markup=keyboard
                    )
                    self.user_states[user_id]['menu_shown'] = True
                    logger.info(f"Showed menu to user {user_id} after {self.user_states[user_id]['message_count']} messages")
                except Exception as e:
                    logger.error(f"Error showing menu to user {user_id}: {e}")
                
        return result 