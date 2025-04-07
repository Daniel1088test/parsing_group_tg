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
import shutil
from telethon import TelegramClient, errors

from tg_bot.keyboards.session_menu import (
    session_menu_keyboard,
    get_sessions_list_keyboard,
    get_session_actions_keyboard
)
from tg_bot.keyboards.main_menu import main_menu_keyboard
from admin_panel.models import TelegramSession
from tg_bot.config import API_ID, API_HASH, ADMIN_ID

router = Router()

class AddSessionStates(StatesGroup):
    waiting_for_phone = State()
    waiting_for_api_id = State()
    waiting_for_api_hash = State()
    waiting_for_code = State()

# keyboard with the cancel button
cancel_keyboard = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="❌ Cancel")]
    ],
    resize_keyboard=True,
    one_time_keyboard=False
)

# Telethon client for authorization
telethon_client = None
telethon_phone = None

# Function to save session file for deployment
async def save_session_to_deployment():
    """Save the Telethon session file content to DATABASE or ENV VAR for deployment"""
    try:
        if os.path.exists('telethon_user_session.session'):
            # Copy to standard session name for consistency
            shutil.copy('telethon_user_session.session', 'telethon_session.session')
            
            # Make backup copies for redundancy
            if not os.path.exists('telethon_session_backup.session'):
                shutil.copy('telethon_session.session', 'telethon_session_backup.session')
            
            # Read and encode the session file for environment variable storage
            with open('telethon_session.session', 'rb') as f:
                session_data = f.read()
                encoded_data = base64.b64encode(session_data).decode('utf-8')
            
            # Save in TelegramSession model for possible use
            @sync_to_async
            def update_or_create_session():
                session, created = TelegramSession.objects.update_or_create(
                    phone='telethon_main',
                    defaults={
                        'api_id': API_ID,
                        'api_hash': API_HASH,
                        'session_file': 'telethon_session',
                        'session_data': encoded_data,
                        'is_active': True
                    }
                )
                return session
            
            await update_or_create_session()
            return True
        return False
    except Exception as e:
        print(f"Error saving session for deployment: {e}")
        return False

@router.message(F.text == "🔑 Add new session")
async def show_session_menu(message: Message):
    """Shows the session management menu"""
    await message.answer(
        "Select an action:",
        reply_markup=session_menu_keyboard
    )

@router.message(F.text == "🔙 Back to main menu")
async def back_to_main_menu(message: Message, state: FSMContext):
    """Returns to the main menu"""
    # clear the FSM state
    await state.clear()
    await message.answer(
        "Main menu:",
        reply_markup=main_menu_keyboard
    )

@router.message(F.text == "❌ Cancel")
async def cancel_action(message: Message, state: FSMContext):
    """Cancelling the action and returning to the session menu"""
    # clear the FSM state
    await state.clear()
    await message.answer(
        "Action cancelled. Select an option:",
        reply_markup=session_menu_keyboard
    )

@router.message(F.text == "🔐 Authorize Telethon")
async def start_telethon_auth(message: Message, state: FSMContext):
    """Starts the Telethon authorization process"""
    # Only admins can use this
    if message.from_user.id != ADMIN_ID:
        await message.answer(
            "❌ This function is only available to administrators.",
            reply_markup=main_menu_keyboard
        )
        return
    
    # Check if session file already exists and offer to delete it
    if os.path.exists('telethon_user_session.session'):
        # Create inline keyboard with button to delete session
        delete_keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="✅ Так, видалити", callback_data="delete_session_file")],
            [InlineKeyboardButton(text="❌ Ні, скасувати", callback_data="cancel_auth")]
        ])
        
        await message.answer(
            "Файл сесії telethon_user_session.session вже існує.\n"
            "Якщо ви маєте проблеми з авторизацією, рекомендується видалити його.\n"
            "Бажаєте видалити існуючий файл сесії?",
            reply_markup=delete_keyboard
        )
        return
    
    await message.answer(
        "Для авторизації в Telethon потрібен ваш номер телефону.\n"
        "Введіть номер телефону у форматі +380XXXXXXXXX:\n"
        "⚠️ ВАЖЛИВО: Ви повинні використовувати звичайний аккаунт користувача, НЕ бота!\n"
        "Щоб скасувати, натисніть кнопку нижче ⬇️",
        reply_markup=cancel_keyboard
    )
    await state.set_state(AddSessionStates.waiting_for_phone)
    # Set flag to indicate this is for Telethon auth
    await state.update_data(is_telethon_auth=True)

@router.callback_query(F.data == "delete_session_file")
async def delete_session_file(callback: CallbackQuery, state: FSMContext):
    """Deleting the Telethon session file"""
    try:
        # Delete all session files
        for session_file in ['telethon_user_session.session', 'telethon_session.session', 'telethon_session_backup.session']:
            if os.path.exists(session_file):
                os.remove(session_file)
                await callback.message.edit_text(
                    f"✅ Файл сесії {session_file} успішно видалено."
                )
        
        # Start authorization process
        await callback.message.answer(
            "Для авторизації в Telethon потрібен ваш номер телефону.\n"
            "Введіть номер телефону у форматі +380XXXXXXXXX:\n"
            "⚠️ ВАЖЛИВО: Ви повинні використовувати звичайний аккаунт користувача, НЕ бота!\n"
            "Щоб скасувати, натисніть кнопку нижче ⬇️",
            reply_markup=cancel_keyboard
        )
        await state.set_state(AddSessionStates.waiting_for_phone)
        await state.update_data(is_telethon_auth=True)
    except Exception as e:
        await callback.message.edit_text(
            f"❌ Помилка видалення файлу сесії: {str(e)}"
        )

@router.callback_query(F.data == "cancel_auth")
async def cancel_auth(callback: CallbackQuery):
    """Cancel the authorization process"""
    await callback.message.edit_text(
        "Авторизацію скасовано. Оберіть інший пункт меню.",
    )
    await callback.message.answer(
        "Оберіть дію:",
        reply_markup=session_menu_keyboard
    )

@router.message(AddSessionStates.waiting_for_phone)
async def process_phone(message: Message, state: FSMContext):
    """Processing the entered phone number"""
    # Check if this is a cancellation
    if message.text == "❌ Cancel":
        await cancel_action(message, state)
        return
    
    phone = message.text.strip()
    try:
        # Phone number validation
        phone_validator = RegexValidator(
            regex=r'^\+\d{10,15}$',
            message='The phone number must be in the format +XXXXXXXXXXX'
        )
        phone_validator(phone)
        
        # Get state data
        state_data = await state.get_data()
        is_telethon_auth = state_data.get('is_telethon_auth', False)
        
        if is_telethon_auth:
            # Store phone for Telethon auth
            await state.update_data(phone=phone)
            
            # Create Telethon client and start authentication
            global telethon_client, telethon_phone
            telethon_phone = phone
            telethon_client = TelegramClient('telethon_user_session', API_ID, API_HASH)
            
            await message.answer(
                "Підключаюсь до Telegram...",
                reply_markup=cancel_keyboard
            )
            
            try:
                await telethon_client.connect()
                
                if await telethon_client.is_user_authorized():
                    me = await telethon_client.get_me()
                    
                    # Save session for deployment
                    deployment_saved = await save_session_to_deployment()
                    deployment_status = "та збережено для розгортання" if deployment_saved else "але не збережено для розгортання (помилка)"
                    
                    await message.answer(
                        f"✅ Ви вже авторизовані як {me.first_name} (@{me.username})!\n"
                        f"Файл сесії дійсний {deployment_status}.",
                        reply_markup=main_menu_keyboard
                    )
                    await state.clear()
                    return
                
                # Request code
                await message.answer(
                    "Будь ласка, зачекайте, запитую код підтвердження...",
                    reply_markup=cancel_keyboard
                )
                
                # Request code from Telegram
                try:
                    await telethon_client.send_code_request(phone)
                    
                    await message.answer(
                        "Telegram надіслав код підтвердження на ваш телефон або у додаток Telegram.\n"
                        "Будь ласка, введіть код:",
                        reply_markup=cancel_keyboard
                    )
                    
                    await state.set_state(AddSessionStates.waiting_for_code)
                except errors.FloodWaitError as e:
                    # Calculate time in hours, minutes, seconds
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
                    
                    # Clean up
                    if telethon_client:
                        await telethon_client.disconnect()
                        telethon_client = None
                        telethon_phone = None
                    
                    await state.clear()
                
            except errors.FloodWaitError as e:
                # Calculate time in hours, minutes, seconds
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
                await message.answer(
                    f"❌ Помилка підключення до Telegram: {str(e)}",
                    reply_markup=session_menu_keyboard
                )
                await state.clear()
            
            return
        
        # For regular session
        # Check if such a number already exists
        phone_exists = await sync_to_async(TelegramSession.objects.filter(phone=phone).exists)()
        if phone_exists:
            await message.answer(
                "This phone number is already registered. Try another:",
                reply_markup=cancel_keyboard
            )
            return
        
        await state.update_data(phone=phone)
        await message.answer(
            "Enter the API ID (https://my.telegram.org/apps):",
            reply_markup=cancel_keyboard
        )
        await state.set_state(AddSessionStates.waiting_for_api_id)
    except ValidationError:
        await message.answer(
            "Incorrect phone number format. Try again:",
            reply_markup=cancel_keyboard
        )

@router.message(AddSessionStates.waiting_for_code)
async def process_code(message: Message, state: FSMContext):
    """Processing the verification code for Telethon"""
    global telethon_client, telethon_phone
    
    if message.text == "❌ Cancel":
        # Clean up
        if telethon_client:
            await telethon_client.disconnect()
            telethon_client = None
            telethon_phone = None
        await cancel_action(message, state)
        return
    
    code = message.text.strip()
    
    try:
        # Try to sign in with the code
        await message.answer(
            "Спроба входу з наданим кодом...",
            reply_markup=cancel_keyboard
        )
        
        try:
            await telethon_client.sign_in(telethon_phone, code)
            
            # Get user info
            me = await telethon_client.get_me()
            
            # Save session for deployment
            deployment_saved = await save_session_to_deployment()
            deployment_status = "та збережено для розгортання" if deployment_saved else "але не збережено для розгортання (помилка)"
            
            await message.answer(
                f"✅ Успішна авторизація як {me.first_name} (@{me.username})!\n"
                f"Файл сесії створено {deployment_status}.\n"
                f"Тепер ви можете використовувати парсинг Telethon.\n\n"
                f"⚠️ ВАЖЛИВО: Перезапустіть сервер для застосування змін!",
                reply_markup=main_menu_keyboard
            )
            
            # Clear state to indicate authorization is complete
            await state.clear()
            
        except errors.SessionPasswordNeededError:
            # Two-factor authentication is enabled
            await message.answer(
                "Для цього аккаунту увімкнена двофакторна автентифікація.\n"
                "Двофакторна автентифікація через інтерфейс бота не підтримується.\n"
                "Будь ласка, створіть новий сеанс через команду: python -m tg_bot.auth_telethon",
                reply_markup=main_menu_keyboard
            )
            await state.clear()
        except errors.PhoneCodeInvalidError:
            await message.answer(
                "❌ Введений код невірний. Спробуйте ще раз:",
                reply_markup=cancel_keyboard
            )
            # Stay in the same state to try again
            return
        except errors.PhoneCodeExpiredError:
            await message.answer(
                "❌ Введений код застарів. Спробуйте запросити новий код, почавши авторизацію спочатку.",
                reply_markup=session_menu_keyboard
            )
            # Clean up and clear state
            if telethon_client:
                await telethon_client.disconnect()
                telethon_client = None
                telethon_phone = None
            await state.clear()
        except Exception as e:
            await message.answer(
                f"❌ Помилка входу: {str(e)}",
                reply_markup=main_menu_keyboard
            )
            await state.clear()
    finally:
        # Clean up resources properly only if authentication is complete or failed with an error
        # We don't clean up on invalid code since we want to allow the user to try again
        if not isinstance(message.text, str) or message.text != "❌ Cancel":
            current_state = await state.get_state()
            if current_state != AddSessionStates.waiting_for_code:
                if telethon_client:
                    await telethon_client.disconnect()
                    telethon_client = None
                    telethon_phone = None

@router.message(F.text == "➕ Add new session")
async def start_add_session(message: Message, state: FSMContext):
    """Starts the process of adding a new session"""
    await message.answer(
        "Enter the phone number in the format +380XXXXXXXXX:\n"
        "To cancel, click the button below ⬇️",
        reply_markup=cancel_keyboard
    )
    await state.set_state(AddSessionStates.waiting_for_phone)
    # Set flag to indicate this is NOT for Telethon auth
    await state.update_data(is_telethon_auth=False)

@router.message(AddSessionStates.waiting_for_api_id)
async def process_api_id(message: Message, state: FSMContext):
    """Processing the entered API ID"""
    # check if this is a cancellation
    if message.text == "❌ Cancel":
        await cancel_action(message, state)
        return
    
    api_id = message.text.strip()
    await state.update_data(api_id=api_id)
    await message.answer(
        "Enter the API Hash (https://my.telegram.org/apps):",
        reply_markup=cancel_keyboard
    )
    await state.set_state(AddSessionStates.waiting_for_api_hash)

@router.message(AddSessionStates.waiting_for_api_hash)
async def process_api_hash(message: Message, state: FSMContext):
    """Processing the entered API Hash and saving the session"""
    # check if this is a cancellation
    if message.text == "❌ Cancel":
        await cancel_action(message, state)
        return
    
    api_hash = message.text.strip()
    data = await state.get_data()
    
    try:
        # create the session asynchronously
        @sync_to_async
        def create_session():
            return TelegramSession.objects.create(
                phone=data['phone'],
                api_id=data['api_id'],
                api_hash=api_hash
            )
        
        session = await create_session()
        await message.answer(
            f"✅ Session successfully added!\n"
            f"Number: {session.phone}\n"
            f"API ID: {session.api_id}",
            reply_markup=session_menu_keyboard
        )
    except Exception as e:
        await message.answer(
            f"❌ Error adding the session: {str(e)}",
            reply_markup=session_menu_keyboard
        )
    
    await state.clear()

@router.message(F.text == "📋 List of sessions")
async def show_sessions_list(message: Message):
    """Displaying the list of all sessions"""
    # get the sessions asynchronously
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
    
    # get the session asynchronously
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

@router.callback_query(F.data.startswith("delete_session_"))
async def delete_session(callback: CallbackQuery):
    """Deleting the session"""
    session_id = int(callback.data.split("_")[2])
    
    # delete the session asynchronously
    @sync_to_async
    def delete_session_by_id(session_id):
        session = TelegramSession.objects.get(id=session_id)
        session.delete()
    
    try:
        await delete_session_by_id(session_id)
        
        # get all sessions after deletion
        @sync_to_async
        def get_all_sessions():
            return list(TelegramSession.objects.all())
        
        sessions = await get_all_sessions()
        
        await callback.message.edit_text(
            "✅ Session successfully deleted!",
            reply_markup=get_sessions_list_keyboard(sessions)
        )
    except Exception as e:
        await callback.message.edit_text(
            f"❌ Error deleting the session: {str(e)}",
            reply_markup=get_session_actions_keyboard(session_id)
        )

@router.callback_query(F.data.startswith("edit_session_"))
async def start_edit_session(callback: CallbackQuery, state: FSMContext):
    """Starting the process of editing the session"""
    session_id = int(callback.data.split("_")[2])
    
    # get the session asynchronously
    @sync_to_async
    def get_session_by_id(session_id):
        return TelegramSession.objects.get(id=session_id)
    
    session = await get_session_by_id(session_id)
    
    await state.update_data(session_id=session_id)
    await callback.message.edit_text(
        "Enter the new API ID:"
    )
    await state.set_state(AddSessionStates.waiting_for_api_id)

@router.callback_query(F.data == "back_to_session_menu")
async def back_to_session_menu(callback: CallbackQuery):
    """Returning to the session menu"""
    # replace the message with the inline buttons with a new message
    await callback.message.delete()
    await callback.message.answer(
        "Select an action:",
        reply_markup=session_menu_keyboard
    )

@router.callback_query(F.data == "back_to_sessions_list")
async def back_to_sessions_list(callback: CallbackQuery):
    """Returning to the list of sessions"""
    # get all sessions asynchronously
    @sync_to_async
    def get_all_sessions():
        return list(TelegramSession.objects.all())
    
    sessions = await get_all_sessions()
    
    await callback.message.edit_text(
        "Select a session:",
        reply_markup=get_sessions_list_keyboard(sessions)
    ) 