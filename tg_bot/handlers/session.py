from aiogram import Router, F, types
from aiogram.filters import Command
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, ReplyKeyboardRemove
from telethon.sessions.string import StringSession
from telethon import TelegramClient
from admin_panel.models import TelegramSession
from tg_bot.config import API_ID, API_HASH
from tg_bot.auth_telethon import input_code, input_password
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
        await message.answer(
            "To authorize your account for Telegram channel parsing, please share your phone number using the button below.\n\n"
            "This will allow the parser to access channels on your behalf."
        )
        
        await message.answer(
            "📱 Please share your phone number:",
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
        # Start the authentication process through Telethon
        from tg_bot.auth_telethon import create_session_file
        
        # Create or update the session in database
        session_obj, created = await TelegramSession.objects.aupdate_or_create(
            phone=phone,
            defaults={
                'api_id': API_ID,
                'api_hash': API_HASH,
                'is_active': True,
                'needs_auth': True
            }
        )
        
        # Store the phone number in user state
        setattr(message.from_user, 'auth_phone', phone)
        setattr(message.from_user, 'auth_session_id', session_obj.id)
        
        # Send progress message
        await message.answer(
            "📲 Connecting to Telegram...",
            reply_markup=ReplyKeyboardRemove()
        )
        
        # Start session file creation in background
        import asyncio
        asyncio.create_task(create_session_file(phone, API_ID, API_HASH))
        
        # Tell user to wait for the code
        await message.answer(
            "🔐 Telegram will send a verification code to your phone or Telegram app.\n\n"
            "Please enter that code here when you receive it. The code should be 5 digits."
        )
        
        # Set code_required flag
        setattr(message.from_user, 'code_required', True)
        
    except Exception as e:
        logger.error(f"Error during authorization: {e}")
        await message.answer(
            "❌ An error occurred during authorization. Please try again later.",
            reply_markup=ReplyKeyboardRemove()
        )

@session_router.message(lambda msg: hasattr(msg.from_user, 'code_required') and msg.text and msg.text.isdigit() and len(msg.text) >= 5)
async def handle_auth_code(message: types.Message):
    """Handle verification code input"""
    code = message.text
    phone = message.from_user.auth_phone
    
    try:
        await message.answer("⏳ Verifying code...")
        
        # Pass the code to the auth system
        result = await input_code(phone, code)
        
        if result == "2FA_REQUIRED":
            # Two-factor authentication is required
            await message.answer(
                "🔒 Two-factor authentication is required.\n\n"
                "Please enter your Telegram account's 2FA password."
            )
            
            # Set 2fa_required flag
            setattr(message.from_user, 'code_required', False)
            setattr(message.from_user, '2fa_required', True)
        elif result:
            # Authentication successful
            # Get current session and update it
            session_id = getattr(message.from_user, 'auth_session_id', None)
            if session_id:
                # Update session in database
                try:
                    session = await TelegramSession.objects.filter(id=session_id).afirst()
                    if session:
                        session.needs_auth = False
                        # Use session_file if it was set during auth
                        if not session.session_file:
                            session.session_file = f"telethon_session_{phone.replace('+', '')}"
                        await session.asave()
                except Exception as e:
                    logger.error(f"Error updating session after auth: {e}")
            
            await message.answer(
                "✅ Authentication successful! Your session has been authorized.\n\n"
                "The parser can now access channels using your account."
            )
            
            # Clear the flags
            delattr(message.from_user, 'code_required')
            delattr(message.from_user, 'auth_phone')
            if hasattr(message.from_user, 'auth_session_id'):
                delattr(message.from_user, 'auth_session_id')
        else:
            # Authentication failed
            await message.answer(
                "❌ Invalid code or authentication failed. Please try again by typing /authorize"
            )
            
            # Clear the flags
            delattr(message.from_user, 'code_required')
            delattr(message.from_user, 'auth_phone')
            if hasattr(message.from_user, 'auth_session_id'):
                delattr(message.from_user, 'auth_session_id')
    except Exception as e:
        logger.error(f"Error in handle_auth_code: {e}")
        await message.answer("❌ An error occurred. Please try again later.")
        
        # Clear the flags
        if hasattr(message.from_user, 'code_required'):
            delattr(message.from_user, 'code_required')
        if hasattr(message.from_user, 'auth_phone'):
            delattr(message.from_user, 'auth_phone')
        if hasattr(message.from_user, 'auth_session_id'):
            delattr(message.from_user, 'auth_session_id')

@session_router.message(lambda msg: hasattr(msg.from_user, '2fa_required') and msg.text)
async def handle_2fa_password(message: types.Message):
    """Handle 2FA password input"""
    password = message.text
    phone = message.from_user.auth_phone
    
    try:
        await message.answer("⏳ Verifying 2FA password...")
        
        # Pass the password to the auth system
        result = await input_password(phone, password)
        
        if result:
            # Authentication successful
            await message.answer(
                "✅ Authentication successful! Your session has been authorized.\n\n"
                "The parser can now access channels using your account."
            )
        else:
            # Authentication failed
            await message.answer(
                "❌ Invalid password or authentication failed. Please try again by typing /authorize"
            )
    except Exception as e:
        logger.error(f"Error in handle_2fa_password: {e}")
        await message.answer("❌ An error occurred. Please try again later.")
    finally:
        # Clear the flags
        if hasattr(message.from_user, '2fa_required'):
            delattr(message.from_user, '2fa_required')
        if hasattr(message.from_user, 'auth_phone'):
            delattr(message.from_user, 'auth_phone')
        if hasattr(message.from_user, 'auth_session_id'):
            delattr(message.from_user, 'auth_session_id')

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