from aiogram import Router, F, types
from aiogram.filters import Command
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, ReplyKeyboardRemove
from admin_panel.models import TelegramSession
from tg_bot.config import API_ID, API_HASH
from tg_bot.keyboards.main_menu import main_menu_keyboard, get_main_menu_keyboard
from tg_bot.keyboards.session_menu import session_menu_keyboard, get_sessions_list_keyboard
from asgiref.sync import sync_to_async
import logging

# Створюємо роутер
session_buttons_router = Router()
logger = logging.getLogger('telegram_bot')

@session_buttons_router.message(F.text == "➕ Add new session")
async def add_new_session(message: types.Message):
    """Handle 'Add new session' button click"""
    try:
        # Redirect to authorization flow
        from tg_bot.handlers.session import start_auth
        await start_auth(message)
    except Exception as e:
        logger.error(f"Error in add_new_session: {e}")
        await message.answer("An error occurred. Please try again later.")

@session_buttons_router.message(F.text == "📋 List of sessions")
async def list_sessions(message: types.Message):
    """Handle 'List of sessions' button click"""
    try:
        # Get sessions from the database
        @sync_to_async
        def get_sessions():
            return list(TelegramSession.objects.all().order_by('-is_active', 'id'))
        
        sessions = await get_sessions()
        
        if not sessions:
            await message.answer(
                "No Telegram sessions found. Please add a new session first.",
                reply_markup=session_menu_keyboard
            )
            return
        
        # Display sessions list
        sessions_text = "📋 Available Telegram sessions:\n\n"
        for idx, session in enumerate(sessions, 1):
            status = "✅ Active" if session.is_active else "❌ Inactive"
            auth_status = "🔓 Needs Auth" if getattr(session, 'needs_auth', True) else "🔒 Authorized"
            sessions_text += f"{idx}. {session.phone} - {status}, {auth_status}\n"
        
        await message.answer(
            sessions_text,
            reply_markup=session_menu_keyboard
        )
    except Exception as e:
        logger.error(f"Error in list_sessions: {e}")
        await message.answer("An error occurred while fetching sessions. Please try again later.")

@session_buttons_router.message(F.text == "🔐 Authorize Telethon")
async def authorize_telethon(message: types.Message):
    """Handle 'Authorize Telethon' button click"""
    try:
        # Get sessions that need authorization
        @sync_to_async
        def get_unauthorized_sessions():
            return list(TelegramSession.objects.filter(is_active=True).order_by('id'))
        
        sessions = await get_unauthorized_sessions()
        
        if not sessions:
            await message.answer(
                "No active Telegram sessions found. Please add a session first.",
                reply_markup=session_menu_keyboard
            )
            return
        
        # If there's only one session, start authorization directly
        if len(sessions) == 1:
            from tg_bot.handlers.session import start_auth
            await message.answer(f"Starting authorization for session {sessions[0].phone}...")
            await start_auth(message)
            return
        
        # Display available sessions for authorization
        sessions_text = "Select a session to authorize:\n\n"
        for idx, session in enumerate(sessions, 1):
            auth_status = "🔓 Needs Auth" if getattr(session, 'needs_auth', True) else "🔒 Authorized"
            sessions_text += f"{idx}. {session.phone} - {auth_status}\n"
        
        # Add instructions
        sessions_text += "\nTo authorize, type /authorize to start the process."
        
        await message.answer(
            sessions_text,
            reply_markup=session_menu_keyboard
        )
    except Exception as e:
        logger.error(f"Error in authorize_telethon: {e}")
        await message.answer("An error occurred. Please try again later.")

@session_buttons_router.message(F.text == "🔙 Back to main menu")
async def back_to_main_menu(message: types.Message):
    """Handle 'Back to main menu' button click"""
    try:
        dynamic_keyboard = await get_main_menu_keyboard()
        await message.answer(
            "Main menu:",
            reply_markup=dynamic_keyboard
        )
    except Exception as e:
        logger.error(f"Error in back_to_main_menu: {e}")
        await message.answer(
            "Returning to main menu...",
            reply_markup=main_menu_keyboard
        ) 