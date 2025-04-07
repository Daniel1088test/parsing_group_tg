from aiogram import Router, F
from aiogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, BufferedInputFile, CallbackQuery
from aiogram.filters import Command
from tg_bot.keyboards.main_menu import main_menu_keyboard
from tg_bot.config import ADMIN_IDS, WEB_SERVER_HOST, WEB_SERVER_PORT, PUBLIC_URL
from admin_panel.models import Channel, Category
from asgiref.sync import sync_to_async
import qrcode
from io import BytesIO
import os
import io

router = Router()

@router.message(Command("start"))
async def cmd_start(message: Message):
    # create a message based on user type
    if str(message.from_user.id) in ADMIN_IDS:
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

@router.message(Command("help"))
async def show_help(message: Message):
    """Show available commands"""
    if str(message.from_user.id) in ADMIN_IDS:
        admin_text = (
            "Admin commands:"
            "\n/ping - check server connection"
            "\n/stop - stop the bot"
            "\n/link_session <session_id> <channel_id> - link session to channel"
            "\n/link_category <session_id> <category_id> - link session to category"
        )
    else:
        admin_text = ""
        
    help_text = (
        "Telegram Parser Bot 🔍"
        "\n\nMain commands:"
        "\n/start - start the bot and show main menu"
        "\n/help - show this help message"
    )
    
    if admin_text:
        help_text += f"\n\n{admin_text}"
    
    await message.answer(help_text, reply_markup=main_menu_keyboard)

@router.message(F.text == "❓ Help")
async def help_button(message: Message):
    # call the function for the /help command
    await show_help(message)

@router.message(F.text == "ℹ️ Information")
async def info_button(message: Message):
    await message.answer(
        "This bot is designed to parse messages from Telegram channels.\n"
        "You can add channels and view parsed messages through the web interface.\n"
        "If you have any questions, please contact the administrator."
    )

@router.message(F.text == "👨‍💻 Support")
async def support_button(message: Message):
    # create a support message with a link to the developer
    support_chat = "your_support_username"  # replace with a real support contact
    await message.answer(
        "If you need technical support, please contact the administrators:\n"
        f"👨‍💻 @{support_chat}"
    )

@router.message(Command("site"))
async def cmd_site(message: Message):
    """Show site URL"""
    # Use the PUBLIC_URL from config, which is set from environment variables
    website_url = PUBLIC_URL
    
    # create a clickable button to go to the site
    site_button = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Open site", url=website_url)],
    ])
    
    # send message with button
    await message.answer(
        f"The site is available at: {website_url}",
        reply_markup=site_button
    )

@router.message(F.text == "🌐 Site")
async def site_button(message: Message):
    """Handler for the 'Go to the site' button"""
    site_url = PUBLIC_URL
    
    # Create inline keyboard
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Open Site 🌐", url=site_url)],
        [InlineKeyboardButton(text="Get QR code", callback_data="qr_code")]
    ])
    
    # Admin section
    if str(message.from_user.id) in ADMIN_IDS:
        admin_text = (
            "As an administrator, you can manage all aspects of the parser from the site:\n"
            "• Add/edit/remove channels and categories\n"
            "• View parsed messages\n"
            "• Configure parser settings\n\n"
        )
    else:
        admin_text = ""
    
    await message.answer(
        f"{admin_text}Click the button below to go to the site:",
        reply_markup=keyboard
    )

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
    
    # check if the message is from admin
    if str(message.from_user.id) in ADMIN_IDS:
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
    
    # check if the message is from admin
    if str(message.from_user.id) in ADMIN_IDS:
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
async def site_button(message: Message):
    """Handler for the 'Go to the site' button"""
    site_url = PUBLIC_URL
    
    # Create inline keyboard
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Open Site 🌐", url=site_url)],
        [InlineKeyboardButton(text="Get QR code", callback_data="qr_code")]
    ])
    
    # Admin section
    if str(message.from_user.id) in ADMIN_IDS:
        admin_text = (
            "As an administrator, you can manage all aspects of the parser from the site:\n"
            "• Add/edit/remove channels and categories\n"
            "• View parsed messages\n"
            "• Configure parser settings\n\n"
        )
    else:
        admin_text = ""
    
    await message.answer(
        f"{admin_text}Click the button below to go to the site:",
        reply_markup=keyboard
    )

@router.callback_query(F.data == "qr_code")
async def process_qr_code(callback: CallbackQuery):
    """Generate and send QR code for the site link"""
    # Use the PUBLIC_URL configuration
    site_url = PUBLIC_URL
    
    # Create QR code
    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_L,
        box_size=10,
        border=4,
    )
    qr.add_data(site_url)
    qr.make(fit=True)
    
    img = qr.make_image(fill_color="black", back_color="white")
    
    # Save to bytes
    img_byte_arr = io.BytesIO()
    img.save(img_byte_arr, format='PNG')
    img_byte_arr.seek(0)
    
    # Admin text
    if str(callback.from_user.id) in ADMIN_IDS:
        caption = f"Admin access QR code for {site_url}"
    else:
        caption = f"QR code for {site_url}"
    
    await callback.message.answer_photo(
        photo=BufferedInputFile(img_byte_arr.read(), filename="qr_code.png"),
        caption=caption
    )
    await callback.answer() 