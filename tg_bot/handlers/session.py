from aiogram import Router, F, types
from aiogram.filters import Command
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton
from telethon.sessions.string import StringSession
from telethon import TelegramClient
from admin_panel.models import TelegramSession
from tg_bot.config import API_ID, API_HASH
import logging

session_router = Router()
logger = logging.getLogger('telegram_bot')

# Keyboard for phone number request
phone_keyboard = ReplyKeyboardMarkup(
    keyboard=[[KeyboardButton(text="Send Phone Number", request_contact=True)]],
    resize_keyboard=True,
    one_time_keyboard=True
)

@session_router.message(Command("authorize"))
async def start_auth(message: types.Message):
    """Start the authorization process"""
    await message.answer(
        "To authorize, please share your phone number using the button below:",
        reply_markup=phone_keyboard
    )

@session_router.message(F.contact)
async def handle_contact(message: types.Message):
    """Handle the received phone number"""
    phone = message.contact.phone_number
    try:
        # Create a new session
        session = StringSession()
        client = TelegramClient(session, API_ID, API_HASH)
        
        # Connect and send code request
        await client.connect()
        code_request = await client.send_code_request(phone)
        
        # Store the phone and hash in the database
        session_obj, created = TelegramSession.objects.get_or_create(
            user_id=message.from_user.id,
            defaults={'phone_number': phone}
        )
        session_obj.phone_hash = code_request.phone_code_hash
        session_obj.save()
        
        await message.answer(
            "I've sent you a code via Telegram. Please send it to me in the format: /code YOUR_CODE",
            reply_markup=types.ReplyKeyboardRemove()
        )
        
    except Exception as e:
        logger.error(f"Error during authorization: {e}")
        await message.answer(
            "An error occurred during authorization. Please try again later.",
            reply_markup=types.ReplyKeyboardRemove()
        )

@session_router.message(Command("code"))
async def handle_code(message: types.Message):
    """Handle the verification code"""
    try:
        code = message.text.split()[1]  # Get the code from message
        session_obj = TelegramSession.objects.get(user_id=message.from_user.id)
        
        # Create session and sign in
        session = StringSession()
        client = TelegramClient(session, API_ID, API_HASH)
        await client.connect()
        
        await client.sign_in(
            phone=session_obj.phone_number,
            code=code,
            phone_code_hash=session_obj.phone_hash
        )
        
        # Save the session string
        session_obj.session_string = client.session.save()
        session_obj.save()
        
        await message.answer("Successfully authorized! Your session has been saved.")
        await client.disconnect()
        
    except Exception as e:
        logger.error(f"Error during code verification: {e}")
        await message.answer("Failed to verify code. Please try /authorize again.")

@session_router.message(Command("check_session"))
async def check_session(message: types.Message):
    """Check if the user has an active session"""
    try:
        session = TelegramSession.objects.get(user_id=message.from_user.id)
        if session.session_string:
            await message.answer("You have an active session.")
        else:
            await message.answer("No active session found. Please use /authorize to create one.")
    except TelegramSession.DoesNotExist:
        await message.answer("No session found. Please use /authorize to create one.") 