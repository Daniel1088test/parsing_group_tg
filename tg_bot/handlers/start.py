from aiogram import Router, types, F
from aiogram.filters import CommandStart
from tg_bot.keyboards.main_menu import main_menu_keyboard
from tg_bot.config import WEB_SERVER_PORT, ADMIN_ID
from aiogram.utils.markdown import hlink
import qrcode
from io import BytesIO
from tg_bot.keyboards.channels_menu import get_channels_keyboard, get_categories_keyboard
from asgiref.sync import async_to_sync, sync_to_async
import logging

# Налаштування логгера
logger = logging.getLogger('tg_bot.handlers.common')

# Створюємо роутер
router = Router()

def _get_categories():
    from admin_panel.models import Category
    return list(Category.objects.all())

def _get_channels():
    from admin_panel.models import Channel
    return list(Channel.objects.all())

# create async functions
get_categories = sync_to_async(_get_categories)
get_channels = sync_to_async(_get_channels)

@router.message(CommandStart())
async def cmd_start(message: types.Message):
    try:
        # Check for deep link parameters (auth token)
        if message.text and len(message.text.split()) > 1:
            auth_token = message.text.split()[1]
            logger.info(f"Received deep link with auth_token: {auth_token}")
            
            # Handle auth token (format: auth_SESSION_ID_TIMESTAMP)
            if auth_token.startswith('auth_'):
                try:
                    parts = auth_token.split('_')
                    if len(parts) >= 3:
                        session_id = int(parts[1])
                        logger.info(f"Processing authorization token for session_id: {session_id}")
                        
                        # Import Django models
                        from admin_panel.models import TelegramSession
                        
                        # Get the session
                        session = await sync_to_async(TelegramSession.objects.get)(id=session_id)
                        if session:
                            # Mark the session as authorized
                            session.is_authorized = True
                            await sync_to_async(session.save)()
                            
                            # Send confirmation to user
                            await message.answer(f"✅ Successfully authorized session for phone: {session.phone}")
                            logger.info(f"Session {session_id} authorized successfully")
                            
                except Exception as auth_error:
                    logger.error(f"Error processing auth token: {auth_error}")
                    await message.answer("❌ Error processing authorization token. Please try again.")
        
        # Створюємо клавіатуру з 4 кнопками
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
        
        # Логуємо інформацію для дебагу
        user_id = message.from_user.id
        username = message.from_user.username or "unknown"
        logger.info(f"Received /start command from user {user_id} (@{username})")
        
        # Відправляємо привітання з клавіатурою
        await message.answer("Привіт! Бот запущено. Використовуйте меню нижче:", reply_markup=keyboard)
        logger.info(f"Start message with 4-button keyboard sent to user {user_id}")
    except Exception as e:
        logger.error(f"Error handling /start command: {e}")
        # Запасний варіант, якщо основний не працює
        try:
            simple_keyboard = types.ReplyKeyboardMarkup(
                keyboard=[
                    [types.KeyboardButton(text="📎 List of channels")],
                    [types.KeyboardButton(text="📍 Categories menu")],
                    [types.KeyboardButton(text="🌐 Go to the site")],
                    [types.KeyboardButton(text="🔑 Add new session")],
                ],
                resize_keyboard=True,
                is_persistent=True
            )
            await message.answer("Привіт! Використовуйте меню:", reply_markup=simple_keyboard)
        except Exception as e2:
            logger.error(f"Critical error in start command: {e2}")
            await message.answer("Бот запущено. Використовуйте команду /menu для відображення кнопок.")

@router.message(F.text == "🌐 Go to the site")   
async def website(message: types.Message):
    # Use external IP address or domain name, if it is configured
    website_url = f"http://192.168.0.237:{WEB_SERVER_PORT}"  # Changed to IP that is displayed when Flask starts
    
    # Create inline keyboard with button to go to the website
    keyboard = types.InlineKeyboardMarkup(inline_keyboard=[
        [types.InlineKeyboardButton(text="Open website", url=website_url)],
        [types.InlineKeyboardButton(text="Get QR code", callback_data="get_qr_code")]
    ])
    
    await message.answer("The website is available at the following link:", reply_markup=keyboard)

@router.callback_query(F.data == "get_qr_code")
async def send_qr_code(callback: types.CallbackQuery):
    website_url = f"http://192.168.0.237:{WEB_SERVER_PORT}"
    
    try:
        # Create QR code for the website
        qr = qrcode.QRCode(
            version=1,
            error_correction=qrcode.constants.ERROR_CORRECT_L,
            box_size=10,
            border=4,
        )
        qr.add_data(website_url)
        qr.make(fit=True)
        
        img = qr.make_image(fill_color="black", back_color="white")
        
        # Save the image to the buffer
        bio = BytesIO()
        img.save(bio, 'PNG')
        bio.seek(0)
        
        # Send the QR code
        await callback.message.answer_photo(
            photo=types.BufferedInputFile(
                file=bio.getvalue(), 
                filename="qrcode.png"
            ),
            caption=f"QR code for access to the website: {website_url}"
        )
        await callback.answer()
    except Exception as e:
        await callback.message.answer(f"Error creating QR code: {e}")
        await callback.answer("Failed to create QR code")

@router.message(F.text == "📎 List of channels")
async def list_channels(message: types.Message, channels_data: dict):
    """
    Displays a list of connected channels
    """
    channels = await get_channels()
    # If the message is from the administrator, provide a keyboard with management buttons
    if message.from_user.id == ADMIN_ID:
        await message.answer("Select a channel:", reply_markup=get_channels_keyboard(channels))
        return
    
    # For regular users, simply show the list
    if not channels:
        await message.answer("The list of channels is empty.")
        return
    
    channels_text = "📎 List of connected channels:\n\n"
    for channel in channels:
        status = "✅ Active" if channel.is_active else "❌ Inactive"
        channels_text += f"• {channel.name} ({status})\n"
    
    await message.answer(channels_text)

@router.message(F.text == "📍 Categories menu")
async def list_categories(message: types.Message, channels_data: dict, categories: dict):
    """
    Displays a list of categories
    """
    categories = await get_categories()
    # If the message is from the administrator, provide a keyboard with management buttons
    if message.from_user.id == ADMIN_ID:
        await message.answer("Select a category:", reply_markup=get_categories_keyboard(channels_data, categories))
        return
    
    # For regular users, simply show the list
    if not categories:
        await message.answer("The list of categories is empty.")
        return
    
    categories_text = "📍 List of categories:\n\n"
    for category in categories:
        categories_text += f"• ID {category.id}: {category.name}\n"
    
    await message.answer(categories_text)