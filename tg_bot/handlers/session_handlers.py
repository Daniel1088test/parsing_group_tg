from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from django.core.exceptions import ValidationError
from django.core.validators import RegexValidator
from asgiref.sync import sync_to_async
import asyncio
import os
import base64
from telethon import TelegramClient, errors
from telethon.sessions import StringSession
import logging

from tg_bot.keyboards.session_menu import (
    session_menu_keyboard,
    get_sessions_list_keyboard,
    get_session_actions_keyboard
)
from tg_bot.keyboards.main_menu import main_menu_keyboard
from admin_panel.models import TelegramSession
from tg_bot.config import API_ID, API_HASH, ADMIN_IDS

router = Router()
logger = logging.getLogger(__name__)

class AddSessionStates(StatesGroup):
    waiting_for_phone = State()
    waiting_for_code = State()
    waiting_for_2fa = State()

# keyboard with the cancel button
cancel_keyboard = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="❌ Cancel")]
    ],
    resize_keyboard=True,
    one_time_keyboard=False
)

# Dictionary to store temporary client data
temp_clients = {}

@router.message(F.text == "🔐 Authorize Telethon")
async def start_telethon_auth(message: Message, state: FSMContext):
    """Start Telethon authorization process"""
    if str(message.from_user.id) not in ADMIN_IDS:
        await message.answer(
            "❌ This function is only available to administrators.",
            reply_markup=main_menu_keyboard
        )
        return
    
    await message.answer(
        "📱 Enter your phone number (with country code):\n"
        "Example: +380123456789\n"
        "⚠️ IMPORTANT: Use a regular user account, NOT a bot!",
        reply_markup=cancel_keyboard
    )
    await state.set_state(AddSessionStates.waiting_for_phone)

@router.message(AddSessionStates.waiting_for_phone)
async def process_phone(message: Message, state: FSMContext):
    """Process the entered phone number"""
    if message.text == "❌ Cancel":
        await cancel_action(message, state)
        return

    phone = message.text.strip()
    
    try:
        # Create new Telethon client
        client = TelegramClient(StringSession(), API_ID, API_HASH)
        await client.connect()
        
        # Store client in temporary storage
        temp_clients[message.from_user.id] = {
            'client': client,
            'phone': phone
        }
        
        # Request verification code
        await client.send_code_request(phone)
        
        await state.set_state(AddSessionStates.waiting_for_code)
        await message.answer(
            "✉️ Enter the verification code you received:",
            reply_markup=cancel_keyboard
        )
        
    except errors.FloodWaitError as e:
        hours, remainder = divmod(e.seconds, 3600)
        minutes, seconds = divmod(remainder, 60)
        time_str = ""
        if hours > 0:
            time_str += f"{hours} годин "
        if minutes > 0:
            time_str += f"{minutes} хвилин "
        if seconds > 0 or (hours == 0 and minutes == 0):
            time_str += f"{seconds} секунд"
            
        await message.answer(
            f"❌ Занадто багато спроб авторизації! Telegram вимагає зачекати {time_str} перед наступною спробою.\n"
            f"Спробуйте пізніше або використайте інший номер телефону.",
            reply_markup=session_menu_keyboard
        )
        await state.clear()
        
    except errors.PhoneNumberInvalidError:
        await message.answer(
            "❌ Невірний формат номера телефону. Спробуйте ще раз:",
            reply_markup=cancel_keyboard
        )
        
    except Exception as e:
        logger.error(f"Error during phone processing: {str(e)}")
        await message.answer(
            f"❌ Помилка підключення до Telegram: {str(e)}",
            reply_markup=session_menu_keyboard
        )
        await state.clear()

@router.message(AddSessionStates.waiting_for_code)
async def process_code(message: Message, state: FSMContext):
    """Process the verification code"""
    if message.text == "❌ Cancel":
        await cancel_action(message, state)
        return
        
    code = message.text.strip()
    
    try:
        # Get client from temporary storage
        client_data = temp_clients.get(message.from_user.id)
        if not client_data:
            await message.answer(
                "❌ Сесія застаріла. Почніть спочатку.",
                reply_markup=session_menu_keyboard
            )
            await state.clear()
            return
            
        client = client_data['client']
        phone = client_data['phone']
        
        # Try to sign in
        try:
            await client.sign_in(phone, code)
            
            # Get session string and encode it to base64
            session_string = client.session.save()
            session_string_encoded = base64.b64encode(session_string.encode()).decode()
            
            # Save to database
            @sync_to_async
            def create_session():
                return TelegramSession.objects.create(
                    phone=phone,
                    api_id=API_ID,
                    api_hash=API_HASH,
                    session_data=session_string_encoded,
                    is_active=True
                )
                
            session = await create_session()
            
            # Get user info
            me = await client.get_me()
            
            await message.answer(
                f"✅ Успішна авторизація як {me.first_name} (@{me.username})!\n"
                f"Сесія створена та активована.\n"
                f"Тепер ви можете використовувати парсинг Telethon.\n\n"
                f"⚠️ ВАЖЛИВО: Перезапустіть сервер для застосування змін!",
                reply_markup=main_menu_keyboard
            )
            
        except errors.SessionPasswordNeededError:
            # 2FA is enabled
            await state.set_state(AddSessionStates.waiting_for_2fa)
            await message.answer(
                "🔐 Для цього аккаунту увімкнена двофакторна автентифікація.\n"
                "Будь ласка, введіть ваш пароль 2FA:",
                reply_markup=cancel_keyboard
            )
            return
            
    except errors.PhoneCodeInvalidError:
        await message.answer(
            "❌ Невірний код. Спробуйте ще раз:",
            reply_markup=cancel_keyboard
        )
        
    except Exception as e:
        logger.error(f"Error during code processing: {str(e)}")
        await message.answer(
            f"❌ Помилка під час авторизації: {str(e)}",
            reply_markup=session_menu_keyboard
        )
        await state.clear()
    finally:
        # Clean up only if we're done or had an error
        current_state = await state.get_state()
        if current_state != AddSessionStates.waiting_for_code and current_state != AddSessionStates.waiting_for_2fa:
            if message.from_user.id in temp_clients:
                try:
                    await temp_clients[message.from_user.id]['client'].disconnect()
                except:
                    pass
                del temp_clients[message.from_user.id]

@router.message(AddSessionStates.waiting_for_2fa)
async def process_2fa(message: Message, state: FSMContext):
    """Process the 2FA password"""
    if message.text == "❌ Cancel":
        await cancel_action(message, state)
        return
        
    password = message.text.strip()
    
    try:
        # Get client from temporary storage
        client_data = temp_clients.get(message.from_user.id)
        if not client_data:
            await message.answer(
                "❌ Сесія застаріла. Почніть спочатку.",
                reply_markup=session_menu_keyboard
            )
            await state.clear()
            return
            
        client = client_data['client']
        phone = client_data['phone']
        
        # Try to complete sign in with 2FA
        await client.sign_in(password=password)
        
        # Get session string and encode it to base64
        session_string = client.session.save()
        session_string_encoded = base64.b64encode(session_string.encode()).decode()
        
        # Save to database
        @sync_to_async
        def create_session():
            return TelegramSession.objects.create(
                phone=phone,
                api_id=API_ID,
                api_hash=API_HASH,
                session_data=session_string_encoded,
                is_active=True
            )
            
        session = await create_session()
        
        # Get user info
        me = await client.get_me()
        
        await message.answer(
            f"✅ Успішна авторизація як {me.first_name} (@{me.username})!\n"
            f"Сесія створена та активована.\n"
            f"Тепер ви можете використовувати парсинг Telethon.\n\n"
            f"⚠️ ВАЖЛИВО: Перезапустіть сервер для застосування змін!",
            reply_markup=main_menu_keyboard
        )
        
    except errors.PasswordHashInvalidError:
        await message.answer(
            "❌ Невірний пароль 2FA. Спробуйте ще раз:",
            reply_markup=cancel_keyboard
        )
        
    except Exception as e:
        logger.error(f"Error during 2FA processing: {str(e)}")
        await message.answer(
            f"❌ Помилка під час авторизації: {str(e)}",
            reply_markup=session_menu_keyboard
        )
        await state.clear()
    finally:
        # Clean up
        if message.from_user.id in temp_clients:
            try:
                await temp_clients[message.from_user.id]['client'].disconnect()
            except:
                pass
            del temp_clients[message.from_user.id]
        await state.clear()

async def cancel_action(message: Message, state: FSMContext):
    """Cancel the current action"""
    # Clean up temporary client if exists
    if message.from_user.id in temp_clients:
        try:
            await temp_clients[message.from_user.id]['client'].disconnect()
        except:
            pass
        del temp_clients[message.from_user.id]
        
    await state.clear()
    await message.answer(
        "❌ Дію скасовано.",
        reply_markup=session_menu_keyboard
    )

@router.message(F.text == "🔙 Back to main menu")
async def back_to_main_menu(message: Message, state: FSMContext):
    """Returns to the main menu"""
    await state.clear()
    await message.answer(
        "Main menu:",
        reply_markup=main_menu_keyboard
    )

@router.message(F.text == "📋 List of sessions")
async def show_sessions_list(message: Message):
    """Displaying the list of all sessions"""
    @sync_to_async
    def get_all_sessions():
        return list(TelegramSession.objects.all())
    
    sessions = await get_all_sessions()
    if not sessions:
        await message.answer(
            "The list of sessions is empty",
            reply_markup=session_menu_keyboard
        )
        return
    
    await message.answer(
        "Select a session:",
        reply_markup=get_sessions_list_keyboard(sessions)
    )

@router.callback_query(F.data.startswith("session_"))
async def show_session_actions(callback: CallbackQuery):
    """Displaying the actions for the selected session"""
    session_id = int(callback.data.split("_")[1])
    
    @sync_to_async
    def get_session_by_id(session_id):
        return TelegramSession.objects.get(id=session_id)
    
    session = await get_session_by_id(session_id)
    
    await callback.message.edit_text(
        f"Information about the session:\n"
        f"Number: {session.phone}\n"
        f"API ID: {session.api_id}\n"
        f"Status: {'Active' if session.is_active else 'Inactive'}\n"
        f"Created: {session.created_at.strftime('%d.%m.%Y %H:%M')}",
        reply_markup=get_session_actions_keyboard(session_id)
    )

@router.callback_query(F.data == "back_to_session_menu")
async def back_to_session_menu(callback: CallbackQuery):
    """Returning to the session menu"""
    await callback.message.edit_text(
        "Select an action:",
        reply_markup=session_menu_keyboard
    ) 