from aiogram import Router, F
from aiogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, BufferedInputFile
from aiogram.filters import Command
from tg_bot.keyboards.main_menu import main_menu_keyboard
from tg_bot.config import ADMIN_ID, WEB_SERVER_HOST, WEB_SERVER_PORT, PUBLIC_URL
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

@router.message(Command("help"))
async def cmd_help(message: Message):
    # show help message
    await message.answer(
        "This bot allows you to parse messages from Telegram channels.\n"
        "Available commands:\n"
        "/start - Start interacting with the bot\n"
        "/help - Show this help message\n"
        "/site - Get the link to the site\n"
        "/qr - Get a QR code for accessing the site"
    )

@router.message(F.text == "❓ Help")
async def help_button(message: Message):
    # call the function for the /help command
    await cmd_help(message)

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
    """Handle site button click"""
    await cmd_site(message)

@router.message(Command("qr"))
async def cmd_qr(message: Message):
    """Generate QR code for site"""
    # Use the PUBLIC_URL from config
    website_url = PUBLIC_URL
    
    # generate a QR code
    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_L,
        box_size=10,
        border=4,
    )
    qr.add_data(website_url)
    qr.make(fit=True)
    
    img = qr.make_image(fill_color="black", back_color="white")
    
    # convert to bytes
    imgByteArr = io.BytesIO()
    img.save(imgByteArr, format='PNG')
    imgByteArr.seek(0)
    
    # send the QR code as a photo
    await message.answer_photo(
        types.BufferedInputFile(
            imgByteArr.getvalue(),
            filename="qr_code.png"
        ),
        caption=f"QR code for access to the site: {website_url}"
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
    # Use 127.0.0.1 if host is localhost
    host = "127.0.0.1" if WEB_SERVER_HOST == "localhost" else WEB_SERVER_HOST
    website_url = f"http://{host}:{WEB_SERVER_PORT}"
    
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
    host = "127.0.0.1" if WEB_SERVER_HOST == "localhost" else WEB_SERVER_HOST
    website_url = f"http://{host}:{WEB_SERVER_PORT}"
    
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