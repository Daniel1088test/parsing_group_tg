from typing import Dict, Any, Callable, Awaitable
from aiogram import BaseMiddleware
from aiogram.types import Message, CallbackQuery, ReplyKeyboardMarkup, KeyboardButton
import logging
from tg_bot.keyboards.main_menu import get_default_keyboard, get_main_menu_keyboard
from asgiref.sync import sync_to_async

logger = logging.getLogger('menu_middleware')

class MenuInitMiddleware(BaseMiddleware):
    """Middleware to ensure users always have a menu visible"""
    
    def __init__(self):
        self.user_states = {}  # Store user interaction states
        logger.info("Menu initialization middleware started")
        
        # Debug log of initialization
        try:
            keyboard = get_default_keyboard()
            logger.info(f"Default keyboard initialized successfully with {len(keyboard.keyboard)} rows")
        except Exception as e:
            logger.error(f"Failed to initialize default keyboard: {e}")
    
    async def __call__(
        self,
        handler: Callable[[Message, Dict[str, Any]], Awaitable[Any]],
        event: Message | CallbackQuery,
        data: Dict[str, Any]
    ) -> Any:
        # Log middleware call
        if isinstance(event, Message):
            user_text = event.text[:20] + '...' if event.text and len(event.text) > 20 else event.text
            logger.info(f"Menu middleware processing message from user {event.from_user.id}: '{user_text}'")
        
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
                logger.info(f"New user {user_id} added to menu tracking")
            
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
                            logger.info(f"Using dynamic keyboard for user {user_id}")
                        except Exception as e:
                            logger.error(f"Error getting dynamic keyboard: {e}")
                            keyboard = get_default_keyboard()
                            logger.info(f"Falling back to default keyboard for user {user_id}")
                            
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
        try:
            result = await handler(event, data)
            logger.debug(f"Handler processed event successfully")
        except Exception as e:
            logger.error(f"Error in handler: {e}")
            # Re-raise to ensure the error is properly handled
            raise
        
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
                        logger.info(f"Using dynamic keyboard for user {user_id} (post-processing)")
                    except Exception as e:
                        logger.error(f"Error getting dynamic keyboard (post): {e}")
                        keyboard = get_default_keyboard()
                        logger.info(f"Falling back to default keyboard for user {user_id} (post-processing)")
                    
                    msg = ("Here's the menu to help you navigate:" if not self.user_states[user_id]['menu_shown'] 
                           else "Remember, you can use these menu options:")
                    
                    # Make sure we have a valid keyboard before sending
                    if keyboard and hasattr(keyboard, 'keyboard') and keyboard.keyboard:
                        logger.info(f"Sending keyboard with {len(keyboard.keyboard)} rows to user {user_id}")
                        await event.answer(msg, reply_markup=keyboard)
                        self.user_states[user_id]['menu_shown'] = True
                        self.user_states[user_id]['last_message_had_menu'] = True
                        logger.info(f"Showed menu to user {user_id} after handling message")
                    else:
                        logger.error(f"Invalid keyboard for user {user_id}: {keyboard}")
                        # Try one last emergency keyboard
                        emergency_keyboard = ReplyKeyboardMarkup(
                            keyboard=[
                                [KeyboardButton(text="📎 List of channels")],
                                [KeyboardButton(text="📍 Categories menu")],
                                [KeyboardButton(text="🌐 Go to the site")],
                                [KeyboardButton(text="🔑 Add new session")],
                            ],
                            resize_keyboard=True,
                            is_persistent=True
                        )
                        await event.answer("Here's a menu to help you navigate:", reply_markup=emergency_keyboard)
                        logger.info(f"Sent emergency keyboard to user {user_id}")
                except Exception as e:
                    logger.error(f"Error showing menu: {e}")
                
        return result 