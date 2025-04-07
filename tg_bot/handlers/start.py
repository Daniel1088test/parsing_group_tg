from aiogram import Router, types, F
from aiogram.filters import CommandStart, Command
from tg_bot.keyboards.main_menu import main_menu_keyboard
from tg_bot.config import WEB_SERVER_PORT, ADMIN_ID, PUBLIC_URL
from aiogram.utils.markdown import hlink
import qrcode
from io import BytesIO
from tg_bot.keyboards.channels_menu import get_channels_keyboard, get_categories_keyboard
from asgiref.sync import async_to_sync, sync_to_async
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

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

@router.message(Command("start"))
async def cmd_start(message: types.Message):
    """
    Command handler for /start
    """
    if message.from_user.id == ADMIN_ID:
        # message for admin
        await message.answer(
            f"Hello, {message.from_user.first_name}!\n"
            "I am your Telegram Parser Bot. I will help you parse messages from Telegram channels.\n"
            "Use the buttons below to control me:",
            reply_markup=admin_menu_keyboard
        )
    else:
        # message for regular user
        await message.answer(
            f"Hello, {message.from_user.first_name}!\n"
            "I am the Telegram Parser Bot.\n"
            "Use the buttons below to interact with me:",
            reply_markup=main_menu_keyboard
        )

@router.message(Command("site"))
async def cmd_site(message: types.Message):
    """Command handler for /site"""
    # Use the PUBLIC_URL from config
    website_url = PUBLIC_URL
    
    # Create a button to open the website
    site_button = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Open website", url=website_url)],
    ])
    
    await message.answer(
        f"You can access the website at: {website_url}",
        reply_markup=site_button
    )

@router.message(Command("qr"))
async def cmd_qr(message: types.Message):
    """Command handler for /qr"""
    # Use the PUBLIC_URL from config
    website_url = PUBLIC_URL
    
    # Generate QR code
    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_L,
        box_size=10,
        border=4,
    )
    qr.add_data(website_url)
    qr.make(fit=True)
    
    img = qr.make_image(fill_color="black", back_color="white")
    
    # Convert to bytes
    img_byte_arr = io.BytesIO()
    img.save(img_byte_arr, format='PNG')
    img_byte_arr.seek(0)
    
    # Send the QR code
    await message.answer_photo(
        types.BufferedInputFile(
            img_byte_arr.getvalue(),
            filename="qr_code.png"
        ),
        caption=f"QR code for access to the website: {website_url}"
    )

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