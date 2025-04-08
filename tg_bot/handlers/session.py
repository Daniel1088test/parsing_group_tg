from aiogram import Router, F, types
from aiogram.filters import Command
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, ReplyKeyboardRemove
from telethon.sessions.string import StringSession
from telethon import TelegramClient
from admin_panel.models import TelegramSession
from tg_bot.config import API_ID, API_HASH
import logging
import base64

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
    try:
        # Check if user already has a session
        existing_session = await TelegramSession.objects.filter(user_id=message.from_user.id).afirst()
        if existing_session and existing_session.session_string:
            await message.answer(
                "You already have an active session. Use /check_session to verify it or contact admin to reset.",
                reply_markup=ReplyKeyboardRemove()
            )
            return
            
        await message.answer(
            "To authorize, please share your phone number using the button below:",
            reply_markup=phone_keyboard
        )
    except Exception as e:
        logger.error(f"Error in start_auth: {e}")
        await message.answer("An error occurred. Please try again later.")

@session_router.message(F.contact)
async def handle_contact(message: types.Message):
    """Handle the received phone number"""
    phone = message.contact.phone_number
    if not phone.startswith('+'):
        phone = '+' + phone
        
    try:
        # Create a new session
        session = StringSession()
        client = TelegramClient(session, API_ID, API_HASH)
        
        # Connect and send code request
        await client.connect()
        code_request = await client.send_code_request(phone)
        
        # Store the phone and hash in the database
        session_obj, created = await TelegramSession.objects.get_or_create(
            phone=phone,
            defaults={
                'user_id': message.from_user.id,
                'api_id': API_ID,
                'api_hash': API_HASH
            }
        )
        session_obj.phone_hash = code_request.phone_code_hash
        await session_obj.asave()
        
        await message.answer(
            "I've sent you a code via Telegram. Please send it to me in the format: /code YOUR_CODE",
            reply_markup=ReplyKeyboardRemove()
        )
        await client.disconnect()
        
    except Exception as e:
        logger.error(f"Error during authorization: {e}")
        await message.answer(
            "An error occurred during authorization. Please try again later.",
            reply_markup=ReplyKeyboardRemove()
        )

@session_router.message(Command("code"))
async def handle_code(message: types.Message):
    """Handle the verification code"""
    try:
        code = message.text.split()[1]  # Get the code from message
        session_obj = await TelegramSession.objects.get(user_id=message.from_user.id)
        
        # Create session and sign in
        session = StringSession()
        client = TelegramClient(session, API_ID, API_HASH)
        await client.connect()
        
        # Sign in and get the session string
        await client.sign_in(
            phone=session_obj.phone,
            code=code,
            phone_code_hash=session_obj.phone_hash
        )
        
        # Get session string and encode it
        session_str = client.session.save()
        encoded_session = base64.b64encode(session_str.encode()).decode()
        
        # Save the session string
        session_obj.session_string = encoded_session
        session_obj.is_active = True
        await session_obj.asave()
        
        await message.answer(
            "Successfully authorized! Your session has been saved and is ready for use.",
            reply_markup=ReplyKeyboardRemove()
        )
        await client.disconnect()
        
    except Exception as e:
        logger.error(f"Error during code verification: {e}")
        await message.answer(
            "Failed to verify code. Please try /authorize again.",
            reply_markup=ReplyKeyboardRemove()
        )

@session_router.message(Command("check_session"))
async def check_session(message: types.Message):
    """Check if the user has an active session"""
    try:
        session = await TelegramSession.objects.get(user_id=message.from_user.id)
        if session.session_string:
            # Try to validate the session
            try:
                session_str = base64.b64decode(session.session_string).decode()
                client = TelegramClient(
                    StringSession(session_str),
                    API_ID,
                    API_HASH
                )
                await client.connect()
                if await client.is_user_authorized():
                    me = await client.get_me()
                    await message.answer(
                        f"Session active and valid! Authorized as: {me.first_name} (@{me.username})",
                        reply_markup=ReplyKeyboardRemove()
                    )
                else:
                    await message.answer(
                        "Session exists but is not authorized. Please use /authorize to create a new session.",
                        reply_markup=ReplyKeyboardRemove()
                    )
                await client.disconnect()
            except Exception as e:
                logger.error(f"Error validating session: {e}")
                await message.answer(
                    "Session exists but appears to be invalid. Please use /authorize to create a new one.",
                    reply_markup=ReplyKeyboardRemove()
                )
        else:
            await message.answer(
                "No active session found. Please use /authorize to create one.",
                reply_markup=ReplyKeyboardRemove()
            )
    except TelegramSession.DoesNotExist:
        await message.answer(
            "No session found. Please use /authorize to create one.",
            reply_markup=ReplyKeyboardRemove()
        )

@session_router.message(lambda msg: msg.text and msg.text.startswith('+') and len(msg.text) > 10 and hasattr(msg.from_user, 'auth_session_id'))
async def handle_auth_phone(message: types.Message):
    """Handle phone number input when authorizing from website"""
    user_id = message.from_user.id
    phone = message.text
    session_id = message.from_user.auth_session_id
    
    try:
        # Get the session
        session = await TelegramSession.objects.filter(id=session_id).afirst()
        if not session:
            await message.answer("Session not found. Please try again.")
            delattr(message.from_user, 'auth_session_id')
            return
            
        from tg_bot.auth_telethon import create_session_file
        
        # Start the auth process
        await message.answer(f"Starting authentication for {phone}. Please wait...")
        
        # Use the session's phone number
        session.phone = phone
        await session.asave()
        
        # Create a session file (this will prompt for code)
        session_file = f"telethon_session_{phone.replace('+', '')}"
        success = await create_session_file(
            phone, 
            session.api_id or API_ID, 
            session.api_hash or API_HASH,
            session_file
        )
        
        if success:
            # Mark session as authenticated
            session.session_file = session_file
            session.needs_auth = False
            await session.asave()
            
            await message.answer(
                "✅ Authentication successful!\n"
                "Your session is now authorized and ready to use.\n"
                "You can now close this chat and return to the website."
            )
        else:
            await message.answer(
                "❌ Authentication failed.\n"
                "Please try again or contact an administrator."
            )
    except Exception as e:
        logger.error(f"Error in handle_auth_phone: {e}")
        await message.answer("An error occurred during authentication. Please try again.")
    finally:
        # Clean up
        if hasattr(message.from_user, 'auth_session_id'):
            delattr(message.from_user, 'auth_session_id')

@session_router.message(lambda msg: msg.text and len(msg.text) >= 5 and msg.text.isdigit() and hasattr(msg.from_user, 'code_required'))
async def handle_auth_code(message: types.Message):
    """Handle verification code input when authorizing from website"""
    code = message.text
    
    try:
        # Get stored session info
        session_id = message.from_user.auth_session_id
        phone = message.from_user.auth_phone
        
        # Signal to the Telethon auth process that we have a code
        from tg_bot.auth_telethon import input_code
        result = await input_code(phone, code)
        
        if result:
            await message.answer(
                "✅ Code accepted! Authentication completed.\n"
                "Your session is now authorized and ready to use.\n"
                "You can now close this chat and return to the website."
            )
        else:
            await message.answer(
                "❌ Invalid code. Please try again."
            )
    except Exception as e:
        logger.error(f"Error in handle_auth_code: {e}")
        await message.answer("An error occurred during code verification. Please try again.")
    finally:
        # Clean up
        if hasattr(message.from_user, 'code_required'):
            delattr(message.from_user, 'code_required')
        if hasattr(message.from_user, 'auth_session_id'):
            delattr(message.from_user, 'auth_session_id')
        if hasattr(message.from_user, 'auth_phone'):
            delattr(message.from_user, 'auth_phone') 