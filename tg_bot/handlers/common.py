from aiogram import Router, F
from aiogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, BufferedInputFile
from aiogram.filters import Command
from tg_bot.keyboards.main_menu import main_menu_keyboard
from tg_bot.config import ADMIN_ID, WEB_SERVER_HOST, WEB_SERVER_PORT
from admin_panel.models import Channel, Category, TelegramSession
from asgiref.sync import sync_to_async
import qrcode
from io import BytesIO
import logging

router = Router()

@router.message(Command("start"))
async def cmd_start(message: Message):
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
                            f"Please follow the instructions to authenticate."
                        )
                        
                        # Import Telethon auth function
                        from tg_bot.auth_telethon import create_session_file
                        
                        # Start the authorization process
                        await message.answer(
                            "For authorization in Telethon, I need your phone number.\n"
                            "Enter your phone number in the format +380XXXXXXXXX:\n"
                            "⚠️ IMPORTANT: You must use a regular user account, NOT a bot!\n"
                            "To cancel, press the button below ⬇️"
                        )
                        
                        # Start the interactive session
                        await message.answer("Please enter your phone number:")
                        
                        # Store auth info in user data
                        await sync_to_async(lambda: setattr(message.from_user, 'auth_session_id', session_id))()
                        return
            except Exception as e:
                logging.error(f"Error processing auth token: {e}")
    
    # If no auth parameter or auth failed, show normal start message
    await message.answer(
        "Welcome! I am a bot for channel parsing.\n"
        "Select an option from the menu below:",
        reply_markup=main_menu_keyboard
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