from typing import Dict, Any, Callable, Awaitable
from aiogram import BaseMiddleware
from aiogram.types import Message, CallbackQuery
import logging
from tg_bot.keyboards.main_menu import get_default_keyboard, get_main_menu_keyboard
from asgiref.sync import sync_to_async

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
        # For message events, check if we need to show the menu BEFORE processing
        if isinstance(event, Message) and event.text:
            user_id = event.from_user.id
            
            # Initialize user state if it's their first interaction
            if user_id not in self.user_states:
                self.user_states[user_id] = {
                    'menu_shown': False,
                    'message_count': 0,
                    'last_message_had_menu': False
                }
            
            # Increment message count
            self.user_states[user_id]['message_count'] += 1
            
            # Only pre-show menu for non-command messages to avoid interference
            if not event.text.startswith('/') and not self.user_states[user_id]['menu_shown']:
                menu_buttons = ["📎 List of channels", "📍 Categories menu", 
                               "🌐 Go to the site", "🔑 Add new session"]
                
                # If this is not a menu button and user hasn't seen menu yet,
                # show the menu immediately before processing if they've sent at least one message
                if (event.text not in menu_buttons and 
                    self.user_states[user_id]['message_count'] >= 1):
                    try:
                        # Try to get the dynamic keyboard first
                        try:
                            keyboard = await get_main_menu_keyboard()
                        except Exception:
                            keyboard = get_default_keyboard()
                            
                        await event.answer(
                            "Here's the menu to help you navigate:",
                            reply_markup=keyboard
                        )
                        self.user_states[user_id]['menu_shown'] = True
                        self.user_states[user_id]['last_message_had_menu'] = True
                        logger.info(f"Pre-shown menu to user {user_id}")
                    except Exception as e:
                        logger.error(f"Error pre-showing menu: {e}")
        
        # Call the handler to process the event
        result = await handler(event, data)
        
        # For message events, check if we need to show the menu AFTER processing
        if isinstance(event, Message) and event.text:
            user_id = event.from_user.id
            
            # Skip for commands or specific menu button texts
            if event.text.startswith('/'):
                return result
                
            menu_buttons = ["📎 List of channels", "📍 Categories menu", 
                           "🌐 Go to the site", "🔑 Add new session"]
            
            # Skip if message is a menu button
            if event.text in menu_buttons:
                self.user_states[user_id]['last_message_had_menu'] = True
                return result
            
            # If we've made it this far and user has never seen menu or hasn't seen it recently
            if (not self.user_states[user_id]['menu_shown'] or 
                not self.user_states[user_id]['last_message_had_menu']):
                try:
                    # Try to get the dynamic keyboard first
                    try:
                        keyboard = await get_main_menu_keyboard()
                    except Exception:
                        keyboard = get_default_keyboard()
                    
                    msg = ("Here's the menu to help you navigate:" if not self.user_states[user_id]['menu_shown'] 
                           else "Remember, you can use these menu options:")
                    
                    await event.answer(msg, reply_markup=keyboard)
                    self.user_states[user_id]['menu_shown'] = True
                    self.user_states[user_id]['last_message_had_menu'] = True
                    logger.info(f"Showed menu to user {user_id} after handling message")
                except Exception as e:
                    logger.error(f"Error showing menu: {e}")
                
        return result 