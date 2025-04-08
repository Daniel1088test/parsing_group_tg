from aiogram import Router, F
from aiogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, BufferedInputFile
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

# Створюємо роутер
common_router = Router()

@common_router.message(Command("start"))
async def cmd_start(message: Message, state: FSMContext):
    """Обробник команди /start"""
    try:
        # Використовуємо безпечний спосіб отримання налаштувань
        settings = await sync_to_async(BotSettings.get_settings)()
        # Показуємо основне меню
        keyboard = InlineKeyboardBuilder()
        
        # Отримуємо всі категорії для меню
        categories = await sync_to_async(list)(Category.objects.filter(is_active=True))
        
        # Додаємо кнопки в меню
        for category in categories:
            keyboard.add(InlineKeyboardButton(
                text=category.name,
                callback_data=f"category_{category.id}"
            ))
        
        # Додаємо додаткові кнопки
        keyboard.row(
            InlineKeyboardButton(text="📊 Аналітика", callback_data="analytics"),
            InlineKeyboardButton(text="ℹ️ Допомога", callback_data="help")
        )
        
        # Відправляємо повідомлення
        welcome_message = (
            f"👋 Вітаємо у Telegram Channel Parser!\n\n"
            f"Цей бот дозволяє збирати повідомлення з Telegram каналів та зберігати їх.\n"
            f"Виберіть категорію для перегляду доступних каналів."
        )
        
        await message.answer(welcome_message, reply_markup=keyboard.as_markup())
    except Exception as e:
        # Безпечна обробка помилок
        logging.error(f"Error in cmd_start: {e}")
        await message.answer(
            "👋 Вітаємо! На жаль, виникла помилка при завантаженні меню. "
            "Спробуйте пізніше або зверніться до адміністратора."
        )

@common_router.message(F.text == "📎 List of channels")
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

@common_router.message(F.text == "📍 Categories menu")
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

@common_router.message(F.text == "🌐 Go to the site")
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

@common_router.callback_query(F.data == "get_qr_code")
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

@common_router.message(F.text == "🔑 Add new session")
async def go_to_session_menu(message: Message):
    """Redirects to the session menu"""
    from tg_bot.keyboards.session_menu import session_menu_keyboard
    
    await message.answer(
        "Select an action:",
        reply_markup=session_menu_keyboard
    )

@common_router.message(Command("help"))
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

@common_router.message(F.text.startswith("python -m"))
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

@common_router.callback_query(F.data == "start_auth")
async def start_auth_from_callback(callback_query):
    """Handle authorize button click"""
    from tg_bot.handlers.session import start_auth
    # Call the start_auth function directly
    await start_auth(callback_query.message)
    await callback_query.answer()

# Catch any possible variations of terminal commands related to authentication
@common_router.message(lambda msg: any(x in msg.text.lower() for x in [
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