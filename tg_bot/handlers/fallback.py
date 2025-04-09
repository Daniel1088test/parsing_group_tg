from aiogram import Router, F, types
from aiogram.filters import Command, CommandStart
from tg_bot.keyboards.main_menu import main_menu_keyboard, get_main_menu_keyboard
import logging

# Створюємо роутер
fallback_router = Router()
logger = logging.getLogger('telegram_bot')

@fallback_router.message(CommandStart())
async def command_start_fallback(message: types.Message):
    """Резервний обробник для команди /start, якщо основний не спрацював"""
    try:
        # Викликаємо основний обробник
        from tg_bot.handlers.common import cmd_start
        await cmd_start(message)
    except Exception as e:
        logger.error(f"Error in command_start_fallback: {e}")
        # Запасний варіант, якщо основний обробник не працює
        dynamic_keyboard = await get_main_menu_keyboard()
        await message.answer(
            "Welcome to Telegram Channel Parser Bot!\nSelect an option from the menu below:",
            reply_markup=dynamic_keyboard
        )

@fallback_router.message(Command("menu"))
async def show_menu(message: types.Message):
    """Додатковий хендлер для швидкого відображення меню"""
    try:
        dynamic_keyboard = await get_main_menu_keyboard()
        await message.answer(
            "Main menu:",
            reply_markup=dynamic_keyboard
        )
    except Exception as e:
        logger.error(f"Error in show_menu: {e}")
        await message.answer(
            "Main menu:", 
            reply_markup=main_menu_keyboard
        )

@fallback_router.message(F.text.startswith("/"))
async def unknown_command(message: types.Message):
    """Обробник для невідомих команд, що починаються з /"""
    commands_help = (
        "Available commands:\n"
        "/start - Show main menu\n"
        "/help - Show help information\n"
        "/authorize - Start session authorization\n"
        "/menu - Show main menu\n"
    )
    await message.answer(
        f"Unknown command: {message.text}\n\n{commands_help}",
        reply_markup=main_menu_keyboard
    )

@fallback_router.message()
async def handle_any_message(message: types.Message):
    """Catch-all handler for all unhandled messages
    
    This handler will be called when no other handler matches
    """
    try:
        logger.info(f"Unhandled message from user {message.from_user.id}: {message.text[:50] if message.text else '<no text>'}")
        
        # Keyboard with main menu buttons
        keyboard = types.ReplyKeyboardMarkup(
            keyboard=[
                [types.KeyboardButton(text="📎 List of channels")],
                [types.KeyboardButton(text="📍 Categories menu")],
                [types.KeyboardButton(text="🌐 Go to the site")],
                [types.KeyboardButton(text="🔑 Add new session")],
            ],
            resize_keyboard=True,
            is_persistent=True
        )
        
        # Send a helpful message with available commands and buttons
        await message.answer(
            "Вибачте, я не розумію цю команду. Використовуйте меню або спробуйте команди:\n"
            "/start - Запустити бота\n"
            "/menu - Показати меню\n"
            "/help - Отримати довідку",
            reply_markup=keyboard
        )
    except Exception as e:
        logger.error(f"Error in fallback handler: {e}")
        # Try to send a simple message without any formatting or keyboards
        try:
            await message.answer("Виникла помилка. Спробуйте команду /start")
        except:
            pass  # If even this fails, just ignore it

@fallback_router.errors()
async def errors_handler(update: types.Update, exception: Exception):
    """Handle errors from other handlers
    
    This handler will catch any exceptions raised in other handlers
    """
    try:
        logger.error(f"Update {update} caused error {exception}")
        
        # Try to get message from update
        message = None
        if hasattr(update, 'message') and update.message:
            message = update.message
        elif hasattr(update, 'callback_query') and update.callback_query and update.callback_query.message:
            message = update.callback_query.message
        
        if message:
            await message.answer(
                "Виникла помилка при обробці запиту. Будь ласка, спробуйте ще раз пізніше або зверніться до адміністратора."
            )
            
            # Try to show main menu again
            keyboard = types.ReplyKeyboardMarkup(
                keyboard=[
                    [types.KeyboardButton(text="📎 List of channels")],
                    [types.KeyboardButton(text="📍 Categories menu")],
                    [types.KeyboardButton(text="🌐 Go to the site")],
                    [types.KeyboardButton(text="🔑 Add new session")],
                ],
                resize_keyboard=True,
                is_persistent=True
            )
            
            await message.answer("Спробуйте використати меню:", reply_markup=keyboard)
            
    except Exception as e:
        # Log but don't try to handle further to avoid infinite loops
        logger.error(f"Error handling error: {e}")
        
    # Return True so aiogram knows the error was handled
    return True 