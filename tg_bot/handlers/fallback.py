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
    """Обробник для будь-яких повідомлень, які не були оброблені іншими хендлерами"""
    try:
        # Не показуємо користувачеві повідомлення про необроблену команду,
        # але показуємо йому кнопки головного меню
        if message.from_user.is_bot:
            return
        
        await show_menu(message)
    except Exception as e:
        logger.error(f"Error in handle_any_message: {e}")
        # Нічого не робимо у разі помилки 