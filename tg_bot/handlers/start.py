from aiogram import Router, types, F
from aiogram.filters import CommandStart
from tg_bot.keyboards.main_menu import main_menu_keyboard
from tg_bot.config import WEB_SERVER_PORT, ADMIN_ID, PUBLIC_HOST
from aiogram.utils.markdown import hlink
import qrcode
from io import BytesIO
from tg_bot.keyboards.channels_menu import get_channels_keyboard, get_categories_keyboard
from asgiref.sync import async_to_sync, sync_to_async
from aiogram.types import Message, CallbackQuery
from tg_bot.keyboards.common import get_start_kb
from tg_bot.keyboards.channels import add_channel_via_message, get_instructions_kb
from tg_bot.utils.messages_utils import parse_username_from_text
from tg_bot.keyboards.auth import get_auth_button

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

@router.message(F.text == "/start")
async def command_start(message: Message):
    """
    This handler will be called when user sends `/start` command
    """
    is_admin = message.from_user.id == ADMIN_ID
    
    reply_markup = get_start_kb(is_admin)
    
    await message.answer(
        "👋 Привет! Я бот для парсинга данных из Telegram.\n\n"
        "Выберите действие из меню ниже:",
        reply_markup=reply_markup,
    )

@router.callback_query(F.data == "add_channel")
async def add_channel_callback(callback: CallbackQuery):
    """Handler for the 'Add channel' callback"""
    # Check if HTTP or HTTPS
    protocol = "https" if PUBLIC_HOST.startswith(("https://", "gondola.proxy.rlwy.net")) else "http"
    website_url = f"{protocol}://{PUBLIC_HOST}"
    
    message = (
        "📱 <b>Инструкция по добавлению канала:</b>\n\n"
        "1. Перешлите мне любое сообщение из канала, который хотите добавить\n"
        "2. Или используйте кнопку ниже, чтобы добавить через веб-интерфейс\n\n"
        "📌 <b>Я могу парсить только публичные каналы!</b>"
    )
    
    await callback.message.edit_text(
        message,
        reply_markup=get_instructions_kb(website_url),
        parse_mode="HTML"
    )

@router.callback_query(F.data == "auth_telethon")
async def auth_telethon_callback(callback: CallbackQuery):
    """Handler for authorization of Telethon"""
    # Check if HTTP or HTTPS
    protocol = "https" if PUBLIC_HOST.startswith(("https://", "gondola.proxy.rlwy.net")) else "http"
    website_url = f"{protocol}://{PUBLIC_HOST}"
    
    await callback.message.edit_text(
        "🔐 <b>Авторизация пользовательского аккаунта для Telethon</b>\n\n"
        "Для полноценной работы парсера нам нужно авторизовать ваш аккаунт Telegram.\n\n"
        "<b>⚠️ ВАЖНО:</b> вы должны использовать <b>обычный аккаунт пользователя</b>, "
        "а не бот-аккаунт! Это необходимо для доступа к API Telegram.\n\n"
        "Нажмите кнопку ниже, чтобы перейти к авторизации:",
        reply_markup=get_auth_button(website_url),
        parse_mode="HTML"
    )

# Message handler for forwarded messages from channels
@router.message(F.forward_from_chat)
async def handle_forwarded_message(message: Message):
    """Handle forwarded message from a channel"""
    await add_channel_via_message(message)

# Message handler for text messages that might contain channel usernames
@router.message(F.text)
async def handle_text_message(message: Message):
    """Handle text message that might contain a channel username"""
    username = parse_username_from_text(message.text)
    if username:
        await add_channel_via_message(message, username)

@router.message(CommandStart())
async def cmd_start(message: types.Message):
    await message.answer("Hello! I am a bot for parsing messages from Telegram channels.", reply_markup=main_menu_keyboard)

@router.message(F.text == "🌐 Go to the website")   
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