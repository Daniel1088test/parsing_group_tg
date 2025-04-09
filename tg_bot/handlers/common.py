from aiogram import Router, F
from aiogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, BufferedInputFile, CallbackQuery, ReplyKeyboardMarkup, KeyboardButton
from aiogram.filters import Command
from tg_bot.keyboards.main_menu import main_menu_keyboard, get_main_menu_keyboard
from tg_bot.config import ADMIN_ID, WEB_SERVER_HOST, WEB_SERVER_PORT
from admin_panel.models import Channel, Category, TelegramSession, BotSettings
from asgiref.sync import sync_to_async
import qrcode
from io import BytesIO
import logging
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.fsm.context import FSMContext

# Configure logging
logger = logging.getLogger(__name__)

# Створюємо роутер
router = Router()

# Handler for /start command with improved reliability
@router.message(Command("start"))
async def cmd_start(message: Message):
    """Handler for /start command"""
    try:
        user_id = message.from_user.id
        username = message.from_user.username or "unknown"
        logger.info(f"Received /start command from user {user_id} (@{username})")
        
        # Create a keyboard directly to ensure it's always available
        fallback_keyboard = ReplyKeyboardMarkup(
            keyboard=[
                [KeyboardButton(text="📎 List of channels")],
                [KeyboardButton(text="📍 Categories menu")],
                [KeyboardButton(text="🌐 Go to the site")],
                [KeyboardButton(text="🔑 Add new session")],
            ],
            resize_keyboard=True,
            is_persistent=True  # Make sure keyboard is persistent
        )
        
        try:
            # Get bot settings
            settings = await sync_to_async(BotSettings.get_settings)()
            
            # Get the appropriate keyboard based on settings
            dynamic_keyboard = await get_main_menu_keyboard()
        except Exception as keyboard_error:
            logger.error(f"Error loading dynamic keyboard: {keyboard_error}")
            dynamic_keyboard = fallback_keyboard
            settings = None
        
        # Check if the message contains a start parameter
        args = message.text.split()
        if len(args) > 1:
            start_param = args[1]
            
            # Check if it's an authorization token
            if start_param.startswith('auth_'):
                # Extract session_id from auth_{session_id}_{timestamp}
                try:
                    parts = start_param.split('_')
                    if len(parts) >= 3:
                        session_id = int(parts[1])
                        
                        # Look up the session in the database
                        session = await sync_to_async(lambda: TelegramSession.objects.filter(id=session_id).first())()
                        
                        if session and session.auth_token == start_param:
                            # Start Telethon authorization
                            await message.answer(
                                f"Starting authorization for session ID {session_id} ({session.phone}).\n"
                                f"Please follow the instructions to authenticate.",
                                reply_markup=fallback_keyboard  # Always include keyboard
                            )
                            
                            # Import Telethon auth function
                            from tg_bot.auth_telethon import create_session_file
                            
                            # Start the authorization process
                            await message.answer(
                                settings.auth_guide_text if settings else 
                                "For authorization in Telethon, I need your phone number.\n"
                                "Please enter your phone number in the format +380XXXXXXXXX:\n"
                                "⚠️ IMPORTANT: You must use a regular user account, NOT a bot!",
                                reply_markup=fallback_keyboard  # Always include keyboard
                            )
                            
                            # Start the interactive session
                            await message.answer("Please enter your phone number:", reply_markup=fallback_keyboard)
                            
                            # Store auth info in user data
                            await sync_to_async(lambda: setattr(message.from_user, 'auth_session_id', session_id))()
                            return
                except Exception as e:
                    logging.error(f"Error processing auth token: {e}")
        
        # If no auth parameter or auth failed, show normal start message
        welcome_msg = "Welcome! I am a bot for channel parsing.\nSelect an option from the menu below:"
        if settings and hasattr(settings, 'welcome_message') and settings.welcome_message:
            welcome_msg = settings.welcome_message
            
        try:
            # Try to send with dynamic keyboard first
            await message.answer(welcome_msg, reply_markup=dynamic_keyboard)
            logger.info(f"Sent welcome message with dynamic keyboard to user {user_id}")
        except Exception as kbd_error:
            # If that fails, try with the fallback keyboard
            logger.error(f"Failed to send dynamic keyboard: {kbd_error}")
            try:
                await message.answer(welcome_msg, reply_markup=fallback_keyboard)
                logger.info(f"Sent welcome message with fallback keyboard to user {user_id}")
            except Exception as fallback_kbd_error:
                logger.error(f"Failed to send fallback keyboard: {fallback_kbd_error}")
                # Last resort - try without keyboard
                await message.answer(f"{welcome_msg}\n\nPlease try sending /menu to show the menu buttons.")
                
                # Force send a menu command
                try:
                    from tg_bot.bot import force_menu
                    await force_menu(message)
                except Exception as force_menu_error:
                    logger.error(f"Failed to force menu: {force_menu_error}")
    except Exception as e:
        logger.error(f"Error handling /start command: {e}")
        # Try sending a simple message as fallback
        try:
            # Create a simple keyboard as last resort
            from aiogram.types import ReplyKeyboardMarkup, KeyboardButton
            emergency_keyboard = ReplyKeyboardMarkup(
                keyboard=[
                    [KeyboardButton(text="📎 List of channels")],
                    [KeyboardButton(text="📍 Categories menu")],
                ],
                resize_keyboard=True,
                is_persistent=True  # Make sure keyboard is persistent
            )
            await message.answer("Привіт! Бот запущено. Використовуйте меню нижче:", reply_markup=emergency_keyboard)
        except Exception as fallback_error:
            logger.error(f"Failed to send fallback message: {fallback_error}")
            # Absolute last resort - no formatting
            await message.answer("Привіт! Бот запущено. Спробуйте /menu для відображення кнопок меню.")

@router.message(F.text == "📎 List of channels")
async def list_channels(message: Message):
    """Shows the list of channels"""
    
    # get the channels from the database
    @sync_to_async
    def get_channels():
        try:
            return list(Channel.objects.all().select_related('category'))
        except Exception as e:
            print(f"Error fetching channels: {e}")
            return []
    
    channels = await get_channels()
    
    if not channels:
        await message.answer(
            "The list of channels is empty.",
            reply_markup=main_menu_keyboard
        )
        return
    
    # check if the message is from the admin
    if message.from_user.id == ADMIN_ID:
        # import the keyboard for the admin
        from tg_bot.keyboards.channels_menu import get_channels_keyboard
        await message.answer(
            "Select a channel:",
            reply_markup=get_channels_keyboard(channels)
        )
        return

    # for ordinary users, show the text list
    channels_text = "📎 List of channels:\n\n"
    for channel in channels:
        status = "✅ Active" if channel.is_active else "❌ Inactive"
        channels_text += f"• {channel.name} ({status})\n  {channel.url}\n  Category: {channel.category.name}\n\n"
    
    await message.answer(
        channels_text,
        reply_markup=main_menu_keyboard
    )

@router.message(F.text == "📍 Categories menu")
async def list_categories(message: Message):
    """Shows the list of categories"""
    
    # get the categories from the database
    @sync_to_async
    def get_categories():
        try:
            return list(Category.objects.all())
        except Exception as e:
            print(f"Error fetching categories: {e}")
            return []
    
    categories = await get_categories()
    
    if not categories:
        await message.answer(
            "The list of categories is empty.",
            reply_markup=main_menu_keyboard
        )
        return
    
    # check if the message is from the admin
    if message.from_user.id == ADMIN_ID:
        # import the keyboard for the admin
        from tg_bot.keyboards.channels_menu import get_categories_keyboard
        await message.answer(
            "Select a category:",
            reply_markup=get_categories_keyboard(None, categories)
        )
        return
    
    categories_text = "📍 List of categories:\n\n"
    for category in categories:
        # get the number of channels in the category
        @sync_to_async
        def count_channels(category_id):
            try:
                return Channel.objects.filter(category_id=category_id).count()
            except Exception as e:
                print(f"Error counting channels: {e}")
                return 0
        
        channel_count = await count_channels(category.id)
        categories_text += f"• {category.name} ({channel_count} channels)\n"
    
    await message.answer(
        categories_text,
        reply_markup=main_menu_keyboard
    )

@router.message(F.text == "🌐 Go to the site")
async def goto_website(message: Message):
    """Sends the link to the site"""
    # Use railway domain if available
    website_url = "https://parsinggrouptg-production.up.railway.app"
    
    # create an inline keyboard with a button to go to the site
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Open site", url=website_url)],
        [InlineKeyboardButton(text="Get QR code", callback_data="get_qr_code")]
    ])
    
    await message.answer(
        f"The site is available at: {website_url}",
        reply_markup=keyboard
    )

@router.callback_query(F.data == "get_qr_code")
async def send_qr_code(callback_query):
    """Sends the QR code for the site"""
    website_url = "https://parsinggrouptg-production.up.railway.app"
    
    try:
        # create a QR code for the site
        qr = qrcode.QRCode(
            version=1,
            error_correction=qrcode.constants.ERROR_CORRECT_L,
            box_size=10,
            border=4,
        )
        qr.add_data(website_url)
        qr.make(fit=True)
        
        img = qr.make_image(fill_color="black", back_color="white")
        
        # save the image to the buffer
        bio = BytesIO()
        img.save(bio, 'PNG')
        bio.seek(0)
        
        # send the QR code
        await callback_query.message.answer_photo(
            photo=BufferedInputFile(
                file=bio.getvalue(), 
                filename="qrcode.png"
            ),
            caption=f"QR code for access to the site: {website_url}"
        )
        await callback_query.answer()
    except Exception as e:
        await callback_query.message.answer(f"Error creating the QR code: {str(e)}")
        await callback_query.answer("Failed to create the QR code")

@router.message(F.text == "🔑 Add new session")
async def go_to_session_menu(message: Message):
    """Redirects to the session menu"""
    from tg_bot.keyboards.session_menu import session_menu_keyboard
    
    await message.answer(
        "Select an action:",
        reply_markup=session_menu_keyboard
    )

@router.message(Command("help"))
async def cmd_help(message: Message):
    """Show help information about authentication and usage"""
    help_text = (
        "📱 <b>Telegram Channel Parser Bot</b>\n\n"
        "This bot helps you authorize Telegram sessions for channel parsing and manage your channels.\n\n"
        "<b>Main Commands:</b>\n"
        "• /start - Show the main menu\n"
        "• /authorize - Start the authorization process for a new session\n"
        "• /help - Show this help message\n\n"
        
        "<b>📋 How to authorize your account:</b>\n"
        "1. Send /authorize command\n"
        "2. Share your phone number when prompted\n"
        "3. Enter the verification code sent by Telegram\n"
        "4. If you have 2FA, enter your password when asked\n\n"
        
        "<b>⚠️ Important notes:</b>\n"
        "• Use a regular Telegram account (not a bot)\n"
        "• The phone number must have access to Telegram\n"
        "• Two-factor authentication (2FA) is fully supported\n"
        "• No terminal commands are needed - everything can be done through this bot\n\n"
        
        "Need more help? Visit the web interface for detailed guides."
    )
    await message.answer(help_text, parse_mode="HTML")

@router.message(F.text.startswith("python -m"))
async def handle_any_python_command(message: Message):
    """Handle any python command, especially those related to tg_bot.auth_telethon"""
    await message.answer(
        "🚫 <b>No need for terminal commands!</b>\n\n"
        "You can authorize your session directly through this bot:\n"
        "1. Send /authorize command\n"
        "2. Share your phone number\n"
        "3. Enter the verification code\n"
        "4. If you have 2FA, enter your password\n\n"
        "This bot fully supports two-factor authentication without any terminal commands.",
        parse_mode="HTML"
    )
    
    # If this appears to be an auth command, suggest immediate authorization
    if "auth_telethon" in message.text or "auth" in message.text:
        # Create an inline keyboard with authorize button
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="Start Authorization Process", callback_data="start_auth")]
        ])
        
        await message.answer(
            "Would you like to start the authorization process now?",
            reply_markup=keyboard
        )

@router.callback_query(F.data == "start_auth")
async def start_auth_from_callback(callback_query):
    """Handle authorize button click"""
    from tg_bot.handlers.session import start_auth
    # Call the start_auth function directly
    await start_auth(callback_query.message)
    await callback_query.answer()

# Catch any possible variations of terminal commands related to authentication
@router.message(lambda msg: any(x in msg.text.lower() for x in [
    "python -m tg_bot.auth_telethon", 
    "python3 -m tg_bot.auth_telethon", 
    "py -m tg_bot.auth_telethon",
    "python manage.py authsession"
]))
async def handle_auth_telethon_command(message: Message):
    """Handle tg_bot.auth_telethon specifically"""
    await message.answer(
        "⚠️ <b>Terminal commands have been replaced!</b>\n\n"
        "Good news! You no longer need to use terminal commands for authentication.\n\n"
        "<b>I'll start the authorization process for you right now.</b>",
        parse_mode="HTML"
    )
    
    # Start the authorization process directly
    from tg_bot.handlers.session import start_auth
    await start_auth(message)

# Catch-all handler for any messages
@router.message()
async def handle_all_messages(message: Message):
    """Handler for all other messages"""
    try:
        user_id = message.from_user.id
        logger.info(f"Received message from user {user_id}: {message.text[:50]}")
        
        # Send a helpful message about commands
        response_text = (
            "Щоб почати роботу, використовуйте команду /start\n"
            "Якщо у вас виникли проблеми, зв'яжіться з адміністратором."
        )
        
        await message.answer(response_text)
    except Exception as e:
        logger.error(f"Error handling message: {e}")

# Create a fallback router to catch any unhandled messages
fallback_router = Router()

@fallback_router.message()
async def fallback_handler(message: Message):
    """Fallback handler for any unhandled messages"""
    try:
        logger.info(f"Fallback handler called for message from user {message.from_user.id}")
        await message.answer("Я не зрозумів цю команду. Спробуйте /start для початку роботи.")
    except Exception as e:
        logger.error(f"Error in fallback handler: {e}")

@fallback_router.callback_query()
async def fallback_callback(callback: CallbackQuery):
    """Fallback handler for any unhandled callback queries"""
    try:
        logger.info(f"Fallback handler called for callback from user {callback.from_user.id}")
        await callback.answer("Ця кнопка більше не активна. Спробуйте /start для оновлення меню.")
    except Exception as e:
        logger.error(f"Error in fallback callback handler: {e}")