from aiogram import types, F, Router, Bot
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from tg_bot.config import ADMIN_ID, FILE_JSON, CATEGORIES_JSON, DATA_FOLDER, MESSAGES_FOLDER
from tg_bot.keyboards.main_menu import main_menu_keyboard
from tg_bot.keyboards.channels_menu import get_channels_keyboard, get_categories_keyboard, get_back_button
import json
import os
import shutil
import uuid
import logging
from asgiref.sync import async_to_sync, sync_to_async
from admin_panel import models
from admin_panel.models import Channel, Category, TelegramSession

# Налаштування логування
logger = logging.getLogger('admin_operations')

router = Router()

# create a synchronous function, which we will then wrap in async
def _create_category(name):
    from admin_panel.models import Category
    return Category.objects.create(name=name)

def _get_category_id(name):
    from admin_panel.models import Category
    return Category.objects.get(name=name).id

def _get_categories():
    from admin_panel.models import Category
    return list(Category.objects.select_related('session').all().order_by('id'))

def _get_category_by_id(id):
    from admin_panel.models import Category
    return Category.objects.select_related('session').get(id=id)

def _create_channel(name, url, category):
    from admin_panel.models import Channel
    return Channel.objects.create(name=name, url=url, category=category)

def _get_channel_by_name(name):
    from admin_panel.models import Channel
    return Channel.objects.select_related('session').get(name=name)

def _get_channel_by_id(id):
    from admin_panel.models import Channel
    return Channel.objects.select_related('session').get(id=id)

# wrap the synchronous function in async
create_category = sync_to_async(_create_category)
get_category_id = sync_to_async(_get_category_id)
get_categories = sync_to_async(_get_categories)
get_category_by_id = sync_to_async(_get_category_by_id)
create_channel = sync_to_async(_create_channel)
get_channel_by_name = sync_to_async(_get_channel_by_name)
get_channel_by_id = sync_to_async(_get_channel_by_id)

# FSM for adding a channel
class AddChannelStates(StatesGroup):
    waiting_for_channel_link = State() 
    waiting_for_channel_name = State()
    waiting_for_channel_category = State()
    waiting_for_channel_session = State()

# FSM for editing a channel
class EditChannelStates(StatesGroup):
    waiting_for_channel_link = State()
    waiting_for_channel_name = State()
    waiting_for_channel_category = State()
    waiting_for_channel_session = State()

# FSM for removing a channel
class RemoveChannelState(StatesGroup):
    waiting_for_input = State()

# FSM for adding a category
class AddCategoryStates(StatesGroup):
    waiting_for_category_name = State()
    waiting_for_category_session = State()

# FSM for editing a category
class EditCategoryStates(StatesGroup):
    waiting_for_category_name = State()
    waiting_for_category_session = State()

# FSM for removing a category
class RemoveCategoryStates(StatesGroup):
    waiting_for_category_id = State()

# New imports for session linking
class SessionLinkStates(StatesGroup):
    waiting_for_channel = State()
    waiting_for_session = State()
    waiting_for_category = State()

@router.message(F.text == "📎 List of channels", F.from_user.id == ADMIN_ID)
async def manage_channels(message: types.Message, channels_data: dict):
    """
    View the list of channels and manage them
    """
    # Get channels from the database
    @sync_to_async
    def get_channels():
        """Get all channels from the database"""
        try:
            # Try using select_related first
            try:
                return list(Channel.objects.select_related('session').all())
            except Exception as e:
                logger.error(f"Error with select_related query: {e}")
                # Fallback to simple query without select_related
                return list(Channel.objects.all())
        except Exception as e:
            logger.error(f"Error getting channels: {e}")
            return []
    
    channels = await get_channels()
    
    if not channels:
        # Create an empty keyboard for the "add channels" message
        empty_keyboard = await prepare_channels_keyboard([])
        await message.answer("The list of channels is empty. Add channels using the buttons below.")
        await message.answer("Select an option:", reply_markup=empty_keyboard)
        return
    
    # Prepare keyboard with async-safe method
    keyboard = await prepare_channels_keyboard(channels)
    await message.answer("Select a channel (🔑 indicates channels with linked session):", reply_markup=keyboard)

@router.callback_query(F.data.startswith("channel_"), F.from_user.id == ADMIN_ID)
async def channel_callback_handler(call: types.CallbackQuery, channels_data: dict):
    """
    Handler for clicking on the channel button
    """
    channel_id = call.data.split("_")[1]
    
    # Get the channel asynchronously
    @sync_to_async
    def get_and_toggle_channel(channel_id):
        try:
            channel = Channel.objects.select_related('session').get(id=channel_id)
            # Change the status of the channel
            old_status = "Active" if channel.is_active else "Inactive"
            channel.is_active = not channel.is_active
            new_status = "Active" if channel.is_active else "Inactive"
            channel.save()
            logger.info(f"The status of channel #{channel.id} '{channel.name}' has been changed: {old_status} -> {new_status}")
            return channel
        except Channel.DoesNotExist:
            logger.error(f"Attempt to change the status of a non-existent channel #{channel_id}")
            return None
    
    channel = await get_and_toggle_channel(channel_id)
    
    if channel:
        # Get all channels to update the keyboard
        @sync_to_async
        def get_all_channels_with_session():
            try:
                # Try with select_related including session
                try:
                    return list(Channel.objects.select_related('session').all())
                except Exception as e:
                    logger.error(f"Error fetching channels with sessions: {e}")
                    # Fallback without select_related
                    return list(Channel.objects.all())
            except Exception as e:
                logger.error(f"Error fetching channels: {e}")
                return []
        
        channels = await get_all_channels_with_session()
        
        # Add session info to the status message if present
        session_info = ""
        if hasattr(channel, '_state') and hasattr(channel._state, 'fields_cache') and 'session' in channel._state.fields_cache:
            session = channel._state.fields_cache.get('session')
            if session and hasattr(session, 'phone'):
                session_info = f" (with session {session.phone})"
        
        # Update the keyboard using async-safe method
        keyboard = await prepare_channels_keyboard(channels)
        
        # Update the keyboard
        await call.message.edit_reply_markup(reply_markup=keyboard)
        await call.answer(f"The status of channel '{channel.name}'{session_info} has been changed!")
    else:
        await call.answer("Channel not found!")

@router.callback_query(F.data.startswith("edit_channel_"), F.from_user.id == ADMIN_ID)
async def edit_channel_start(call: types.CallbackQuery, state: FSMContext, channels_data: dict):
    """
    Start the process of editing a channel
    """
    channel_id = call.data.split("_")[2]
    
    @sync_to_async
    def get_channel_by_id_with_data(channel_id):
        try:
            try:
                # Try with select_related first
                channel = Channel.objects.select_related('session', 'category').get(id=channel_id)
            except Exception as e:
                logger.error(f"Error getting channel with select_related: {e}")
                # Fallback to basic query without select_related
                channel = Channel.objects.get(id=channel_id)
            
            # Build channel data with safe access to related objects
            data = {
                "id": channel.id,
                "name": channel.name,
                "url": channel.url,
                "category_id": channel.category_id,
                "category_name": None,  # Default value
                "is_active": channel.is_active,
                "session_id": None,     # Default value
                "session_phone": None   # Default value
            }
            
            # Safely get category name
            try:
                if hasattr(channel, 'category') and channel.category:
                    data["category_name"] = channel.category.name
            except Exception as cat_err:
                logger.error(f"Error accessing category name: {cat_err}")
            
            # Safely get session info
            try:
                if hasattr(channel, 'session') and channel.session:
                    data["session_id"] = channel.session.id
                    data["session_phone"] = channel.session.phone
            except Exception as sess_err:
                logger.error(f"Error accessing session info: {sess_err}")
            
            return data
        except Channel.DoesNotExist:
            logger.error(f"Channel with ID {channel_id} does not exist")
            return None
        except Exception as e:
            logger.error(f"Error getting channel data: {e}")
            return None
    
    channel_data = await get_channel_by_id_with_data(channel_id)
    
    if channel_data:
        # Save the channel ID in the state
        await state.update_data(channel_id=channel_id)
        await state.update_data(current_data=channel_data)
        
        # Build channel info message with session info
        channel_info = f"Editing channel: {channel_data['name']}\n"
        channel_info += f"Current link: {channel_data['url']}\n"
        channel_info += f"Current category: {channel_data['category_name']} (ID: {channel_data['category_id']})\n"
        
        if channel_data['session_phone']:
            channel_info += f"Current session: {channel_data['session_phone']} (ID: {channel_data['session_id']})\n"
        else:
            channel_info += "Current session: None\n"
            
        await call.message.answer(channel_info)
        await call.message.answer("Enter a new link or click /skip to leave the current link:")
        await state.set_state(EditChannelStates.waiting_for_channel_link)
        await call.answer()
    else:
        await call.answer("Channel not found!")

@router.message(EditChannelStates.waiting_for_channel_link, F.text, F.from_user.id == ADMIN_ID)
async def process_edit_channel_link(message: types.Message, state: FSMContext):
    """
    get a new channel link
    """
    if message.text == "/skip":
        user_data = await state.get_data()
        await state.update_data(new_channel_link=user_data['current_data']['url'])
    else:
        channel_link = message.text.strip()
        if channel_link.startswith("https://t.me/"):
            await state.update_data(new_channel_link=channel_link)
        else:
            await message.answer("Incorrect channel link. Enter a link in the format 'https://t.me/username':")
            return

    await message.answer("Enter a new channel name or click /skip to leave the current name:")
    await state.set_state(EditChannelStates.waiting_for_channel_name)

@router.message(EditChannelStates.waiting_for_channel_name, F.text, F.from_user.id == ADMIN_ID)
async def process_edit_channel_name(message: types.Message, state: FSMContext):
    """
    get a new channel name
    """
    if message.text == "/skip":
        user_data = await state.get_data()
        await state.update_data(new_channel_name=user_data['current_data']['name'])
    else:
        await state.update_data(new_channel_name=message.text)
    
    # Get categories with session info asynchronously
    @sync_to_async
    def get_ordered_categories_with_session():
        try:
            # First try with select_related including session
            try:
                return list(Category.objects.select_related('session').all().order_by('id'))
            except Exception as e:
                logger.error(f"Error fetching categories with session: {e}")
                # Fallback without select_related
                return list(Category.objects.all().order_by('id'))
        except Exception as e:
            logger.error(f"Error fetching categories: {e}")
            return []
    
    categories = await get_ordered_categories_with_session()
    user_data = await state.get_data()
    current_category_id = user_data['current_data']['category_id']
    
    # Create mapping of display indices to actual category IDs
    category_mapping = {}
    category_text = "Select the number of the category from the list or click /skip to leave the current one:\n"
    
    for idx, category in enumerate(categories, 1):
        category_mapping[idx] = category.id
        session_info = f" (Session: {category.session.phone})" if category.session else ""
        marker = "➡️ " if category.id == current_category_id else ""
        category_text += f"{marker}{idx}: {category.name}{session_info}\n"
    
    # Store the mapping in the state
    await state.update_data(category_mapping=category_mapping)
    
    await message.answer(category_text)
    await state.set_state(EditChannelStates.waiting_for_channel_category)

@router.message(EditChannelStates.waiting_for_channel_category, F.text, F.from_user.id == ADMIN_ID)
async def process_edit_channel_category(message: types.Message, state: FSMContext, channels_data: dict):
    """
    get a new channel category and proceed to session selection
    """
    user_data = await state.get_data()
    channel_id = user_data['channel_id']
    category_mapping = user_data.get('category_mapping', {})
    
    # Determine the new category
    if message.text == "/skip":
        new_category_id = user_data['current_data']['category_id']
    else:
        # Parse input as display index
        try:
            display_index = int(message.text)
            # Get the actual category ID from the mapping
            if display_index in category_mapping:
                category_id = category_mapping[display_index]
            else:
                await message.answer("Invalid category number. Please enter a number from the list or use /skip")
                return
        except ValueError:
            await message.answer("Enter a numerical category number or use /skip")
            return
            
        # Check if the specified category exists
        @sync_to_async
        def check_category_exists(category_id):
            try:
                return Category.objects.select_related('session').get(id=category_id)
            except Category.DoesNotExist:
                return None
        
        category = await check_category_exists(category_id)
        if not category:
            await message.answer("Category not found. Try again or use /skip")
            return
        
        new_category_id = category_id
        
        # If the category has a session, suggest using it
        if category.session:
            await message.answer(f"Note: The selected category is linked to session {category.session.phone} (ID: {category.session.id})")
    
    # Save the new category ID to state
    await state.update_data(new_category_id=new_category_id)
    
    # Get available sessions for selection
    @sync_to_async
    def get_active_sessions():
        try:
            # Try to filter active sessions
            try:
                # Safely handle fields that might be missing
                return list(TelegramSession.objects.filter(is_active=True).order_by('phone'))
            except Exception as field_error:
                logger.error(f"Error filtering active sessions: {field_error}")
                # Fallback to all sessions
                return list(TelegramSession.objects.all().order_by('phone'))
        except Exception as e:
            logger.error(f"Error fetching sessions: {e}")
            return []
    
    # Get current session info
    @sync_to_async
    def get_channel_session(channel_id):
        channel = Channel.objects.get(id=channel_id)
        return channel.session
    
    sessions = await get_active_sessions()
    current_session = await get_channel_session(channel_id)
    
    if sessions:
        # Create mapping of display indices to actual session IDs
        session_mapping = {}
        sessions_text = "Select a Telegram session ID for this channel (type number, 0 to unlink, or /skip to keep current):\n"
        
        for idx, session in enumerate(sessions, 1):
            session_mapping[idx] = session.id
            marker = "➡️ " if current_session and session.id == current_session.id else ""
            sessions_text += f"{marker}{idx}: {session.phone}\n"
        
        # Store the mapping in the state
        await state.update_data(session_mapping=session_mapping)
        
        await message.answer(sessions_text)
        await state.set_state(EditChannelStates.waiting_for_channel_session)
    else:
        # If no sessions, skip to channel update
        await message.answer("No active sessions found. The channel will keep its current session setting.")
        await update_channel_with_data(message, state, channels_data, None, True)

@router.message(EditChannelStates.waiting_for_channel_session, F.text, F.from_user.id == ADMIN_ID)
async def process_edit_channel_session(message: types.Message, state: FSMContext, channels_data: dict):
    """
    get the new channel session and save the data
    """
    user_data = await state.get_data()
    channel_id = user_data['channel_id']
    session_mapping = user_data.get('session_mapping', {})
    
    # Skip option - keep current session
    if message.text == "/skip":
        await update_channel_with_data(message, state, channels_data, None, True)
        return
        
    # Unlink option
    if message.text == "0":
        await update_channel_with_data(message, state, channels_data, 0, False)
        return
    
    # Validate the session index
    try:
        display_index = int(message.text)
        # Get the actual session ID from the mapping
        if display_index in session_mapping:
            session_id = session_mapping[display_index]
        else:
            await message.answer("Invalid session number. Please enter a number from the list, use 0 to unlink, or /skip to keep current.")
            return
    except ValueError:
        await message.answer("The session number must be a number. Please try again, use 0 to unlink, or /skip to keep current.")
        return
    
    # Check if session exists
    @sync_to_async
    def check_session_exists(session_id):
        try:
            return TelegramSession.objects.get(id=session_id, is_active=True)
        except TelegramSession.DoesNotExist:
            return None
    
    session = await check_session_exists(session_id)
    if not session:
        await message.answer("Session not found or inactive. Please try again, use 0 to unlink, or /skip to keep current.")
        return
    
    # Update the channel with the selected session
    await update_channel_with_data(message, state, channels_data, session_id, False)

async def update_channel_with_data(message: types.Message, state: FSMContext, channels_data: dict, session_id=None, keep_current=False):
    """
    Update a channel with the collected data
    """
    # Get data from state
    user_data = await state.get_data()
    channel_id = user_data['channel_id']
    new_name = user_data['new_channel_name']
    new_url = user_data['new_channel_link']
    new_category_id = user_data.get('new_category_id', user_data['current_data']['category_id'])
    
    # Update the channel in the database
    @sync_to_async
    def update_channel_in_db(channel_id, new_name, new_url, new_category_id, session_id, keep_current):
        try:
            channel = Channel.objects.get(id=channel_id)
            old_data = {
                "name": channel.name,
                "url": channel.url,
                "category_id": channel.category_id,
                "session": channel.session.phone if channel.session else None
            }
            
            # Update basic fields
            channel.name = new_name
            channel.url = new_url
            channel.category_id = new_category_id
            
            # Handle session update
            if not keep_current:
                if session_id == 0:
                    channel.session = None
                elif session_id:
                    channel.session = TelegramSession.objects.get(id=session_id)
                    
            channel.save()
            
            # Log changes
            logger.info(f"Updated channel #{channel_id}:")
            if old_data['name'] != new_name:
                logger.info(f"- Name: '{old_data['name']}' -> '{new_name}'")
            if old_data['url'] != new_url:
                logger.info(f"- URL: '{old_data['url']}' -> '{new_url}'")
            if old_data['category_id'] != new_category_id:
                logger.info(f"- Category: {old_data['category_id']} -> {new_category_id}")
            
            new_session = channel.session.phone if channel.session else None
            if old_data['session'] != new_session:
                logger.info(f"- Session: {old_data['session']} -> {new_session}")
                
            return True, channel.name, new_session
        except Exception as e:
            logger.error(f"Error updating channel #{channel_id}: {e}")
            return False, None, None
    
    result, channel_name, session_info = await update_channel_in_db(
        channel_id, 
        new_name, 
        new_url, 
        new_category_id,
        session_id,
        keep_current
    )
    
    if result:
        # Get all channels to update the keyboard
        @sync_to_async
        def get_all_channels_with_session():
            try:
                # Try with select_related including session
                try:
                    return list(Channel.objects.select_related('session').all())
                except Exception as e:
                    logger.error(f"Error fetching channels with sessions: {e}")
                    # Fallback without select_related
                    return list(Channel.objects.all())
            except Exception as e:
                logger.error(f"Error fetching channels: {e}")
                return []
        
        channels = await get_all_channels_with_session()
        
        session_text = ""
        if session_info:
            session_text = f" with session {session_info}"
        elif session_id == 0:
            session_text = " with no session (unlinked)"
            
        # Prepare keyboard with async-safe method
        keyboard = await prepare_channels_keyboard(channels)
        
        await message.answer(
            f"✅ Channel '{channel_name}' updated successfully{session_text}!", 
            reply_markup=keyboard
        )
    else:
        await message.answer("❌ Error updating the channel.")
    
    await state.clear()

@router.callback_query(F.data.startswith("category_"), F.from_user.id == ADMIN_ID)
async def category_callback_handler(call: types.CallbackQuery, channels_data: dict):
    """
    Handler for clicking on the category button
    """
    category_id = call.data.split("_")[1]
    
    # Get channels by category
    @sync_to_async
    def get_channels_by_category(category_id):
        return list(Channel.objects.select_related('session').filter(category_id=category_id))
    
    channels = await get_channels_by_category(category_id)
    
    # Get the category name and session info
    @sync_to_async
    def get_category_info(category_id):
        try:
            try:
                # Try with select_related first
                category = Category.objects.select_related('session').get(id=category_id)
            except Exception as e:
                logger.error(f"Error fetching category with select_related: {e}")
                # Fallback to basic query
                category = Category.objects.get(id=category_id)
            
            # Build info dict with safe access to session
            info = {
                'name': category.name,
                'session': None  # Default value
            }
            
            # Safely get session info if available
            try:
                if hasattr(category, 'session') and category.session:
                    info['session'] = category.session.phone
            except Exception as sess_err:
                logger.error(f"Error accessing session for category {category_id}: {sess_err}")
            
            return info
        except Category.DoesNotExist:
            logger.warning(f"Category with ID {category_id} not found")
            return {'name': "Unknown category", 'session': None}
        except Exception as e:
            logger.error(f"Error getting category info for ID {category_id}: {e}")
            return {'name': "Error", 'session': None}
    
    category_info = await get_category_info(category_id)
    
    # Add session information if present
    category_name = category_info['name']
    if category_info['session']:
        category_name += f" (Session: {category_info['session']})"
    
    # Prepare keyboard in an async-safe way
    keyboard = await prepare_channels_keyboard(channels, category_id)
    
    await call.message.edit_text(
        f"Channels of category '{category_name}':", 
        reply_markup=keyboard
    )
    await call.answer()

@router.callback_query(F.data == "back")
async def handle_back(callback: types.CallbackQuery, state: FSMContext, channels_data: dict = None):
    """
    Universal handler for back button clicks
    """
    current_state = await state.get_state()
    
    if current_state == SessionLinkStates.waiting_for_session:
        # Go back to channel selection when in session linking flow
        @sync_to_async
        def get_channels():
            return list(Channel.objects.select_related('session').all().order_by('name'))
        
        channels = await get_channels()
        keyboard = await prepare_channels_keyboard(channels)
        
        await callback.message.edit_text(
            "Select a channel to link to a session:",
            reply_markup=keyboard
        )
        
        await state.set_state(SessionLinkStates.waiting_for_channel)
    elif channels_data is not None and callback.from_user.id == ADMIN_ID:
        # When returning from a category's channel list to category menu
        @sync_to_async
        def get_categories_with_sessions():
            return list(Category.objects.select_related('session').all().order_by('id'))
        
        categories = await get_categories_with_sessions()
        keyboard = await prepare_categories_keyboard(channels_data, categories)
        
        await callback.message.edit_text("Select an action:", reply_markup=keyboard)
        await callback.answer()
    else:
        # Default case: clear state and go back to main menu
        await state.clear()
        await callback.message.edit_text("Operation cancelled.")
        await callback.message.answer("Main menu:", reply_markup=main_menu_keyboard)

@router.message(F.text == "📍 Categories menu", F.from_user.id == ADMIN_ID)
async def manage_categories(message: types.Message, channels_data: dict):
    """
    manage the list of categories
    """
    # Get categories with session info
    @sync_to_async
    def get_ordered_categories_with_session():
        try:
            # First try with select_related including session
            try:
                return list(Category.objects.select_related('session').all().order_by('id'))
            except Exception as e:
                logger.error(f"Error fetching categories with session: {e}")
                # Fallback without select_related
                return list(Category.objects.all().order_by('id'))
        except Exception as e:
            logger.error(f"Error fetching categories: {e}")
            return []
    
    categories = await get_ordered_categories_with_session()
    keyboard = await prepare_categories_keyboard(channels_data, categories)
    
    await message.answer("Select a category (🔑 indicates categories with linked session):", 
                         reply_markup=keyboard)

@router.callback_query(F.data.startswith("edit_category_"), F.from_user.id == ADMIN_ID)
async def edit_category_start(call: types.CallbackQuery, state: FSMContext):
    """
    start the process of editing a category
    """
    category_id = call.data.split("_")[2]
    
    @sync_to_async
    def get_category_details(category_id):
        try:
            category = Category.objects.select_related('session').get(id=category_id)
            return {
                'id': category.id,
                'name': category.name,
                'session_id': category.session.id if category.session else None,
                'session_phone': category.session.phone if category.session else None
            }
        except Category.DoesNotExist:
            return None
    
    category_data = await get_category_details(category_id)
    
    if category_data:
        await state.update_data(category_id=category_data['id'])
        await state.update_data(current_category_name=category_data['name'])
        
        # Build category info message with session info
        category_info = f"Editing category: {category_data['name']}\n"
        
        if category_data['session_phone']:
            category_info += f"Current session: {category_data['session_phone']} (ID: {category_data['session_id']})\n"
        else:
            category_info += "Current session: None\n"
            
        await call.message.answer(category_info)
        await call.message.answer("Enter a new category name:")
        await state.set_state(EditCategoryStates.waiting_for_category_name)
        await call.answer()
    else:
        await call.answer("Category not found!")

@router.message(EditCategoryStates.waiting_for_category_name, F.text, F.from_user.id == ADMIN_ID)
async def process_edit_category_name(message: types.Message, state: FSMContext, channels_data: dict):
    """
    get a new category name and proceed to session selection
    """
    category_name = message.text
    user_data = await state.get_data()
    category_id = user_data['category_id']
    
    # Update state with new name
    await state.update_data(new_category_name=category_name)
    
    # Get available sessions for selection
    @sync_to_async
    def get_active_sessions():
        try:
            # Try to filter active sessions
            try:
                # Safely handle fields that might be missing
                return list(TelegramSession.objects.filter(is_active=True).order_by('phone'))
            except Exception as field_error:
                logger.error(f"Error filtering active sessions: {field_error}")
                # Fallback to all sessions
                return list(TelegramSession.objects.all().order_by('phone'))
        except Exception as e:
            logger.error(f"Error fetching sessions: {e}")
            return []
    
    # Get current session info
    @sync_to_async
    def get_category_session(category_id):
        category = Category.objects.get(id=category_id)
        return category.session
    
    sessions = await get_active_sessions()
    current_session = await get_category_session(category_id)
    
    if sessions:
        # Create mapping of display indices to actual session IDs
        session_mapping = {}
        sessions_text = "Select a Telegram session for this category (enter number, 0 to unlink, or /skip to keep current):\n"
        
        for idx, session in enumerate(sessions, 1):
            session_mapping[idx] = session.id
            marker = "➡️ " if current_session and session.id == current_session.id else ""
            sessions_text += f"{marker}{idx}: {session.phone}\n"
        
        # Store the mapping in the state
        await state.update_data(session_mapping=session_mapping)
        
        await message.answer(sessions_text)
        await state.set_state(EditCategoryStates.waiting_for_category_session)
    else:
        # If no sessions, skip to category update
        await message.answer("No active sessions found. The category will keep its current session setting.")
        await update_category_with_data(message, state, channels_data, None, True)

@router.message(EditCategoryStates.waiting_for_category_session, F.text, F.from_user.id == ADMIN_ID)
async def process_edit_category_session(message: types.Message, state: FSMContext, channels_data: dict):
    """
    get the new category session and save the data
    """
    user_data = await state.get_data()
    category_id = user_data['category_id']
    session_mapping = user_data.get('session_mapping', {})
    
    # Skip option - keep current session
    if message.text == "/skip":
        await update_category_with_data(message, state, channels_data, None, True)
        return
        
    # Unlink option
    if message.text == "0":
        await update_category_with_data(message, state, channels_data, 0, False)
        return
    
    # Validate the session index
    try:
        display_index = int(message.text)
        # Get the actual session ID from the mapping
        if display_index in session_mapping:
            session_id = session_mapping[display_index]
        else:
            await message.answer("Invalid session number. Please enter a number from the list, use 0 to unlink, or /skip to keep current.")
            return
    except ValueError:
        await message.answer("The session number must be a number. Please try again, use 0 to unlink, or /skip to keep current.")
        return
    
    # Check if session exists
    @sync_to_async
    def check_session_exists(session_id):
        try:
            return TelegramSession.objects.get(id=session_id, is_active=True)
        except TelegramSession.DoesNotExist:
            return None
    
    session = await check_session_exists(session_id)
    if not session:
        await message.answer("Session not found or inactive. Please try again, use 0 to unlink, or /skip to keep current.")
        return
    
    # Update the category with the selected session
    await update_category_with_data(message, state, channels_data, session_id, False)

async def update_category_with_data(message: types.Message, state: FSMContext, channels_data: dict, session_id=None, keep_current=False):
    """
    Update a category with the collected data
    """
    # Get data from state
    user_data = await state.get_data()
    category_id = user_data['category_id']
    new_name = user_data['new_category_name']
    
    # Update the category in the database
    @sync_to_async
    def update_category_in_db(category_id, new_name, session_id, keep_current):
        try:
            category = Category.objects.get(id=category_id)
            old_name = category.name
            old_session = category.session.phone if category.session else None
            
            # Update name
            category.name = new_name
            
            # Handle session update
            if not keep_current:
                if session_id == 0:
                    category.session = None
                elif session_id:
                    category.session = TelegramSession.objects.get(id=session_id)
                    
            category.save()
            
            # Log changes
            if old_name != new_name:
                logger.info(f"Updated category #{category_id}: Name '{old_name}' -> '{new_name}'")
            
            new_session = category.session.phone if category.session else None
            if old_session != new_session:
                logger.info(f"Updated category #{category_id}: Session {old_session} -> {new_session}")
                
            return True, new_name, new_session
        except Exception as e:
            logger.error(f"Error updating category #{category_id}: {e}")
            return False, None, None
    
    result, category_name, session_info = await update_category_in_db(
        category_id, 
        new_name,
        session_id,
        keep_current
    )
    
    if result:
        # Get updated categories list with sessions
        @sync_to_async
        def get_ordered_categories_with_session():
            return list(Category.objects.select_related('session').all().order_by('id'))
        
        categories = await get_ordered_categories_with_session()
        keyboard = await prepare_categories_keyboard(channels_data, categories)
        
        session_text = ""
        if session_info:
            session_text = f" with session {session_info}"
        elif session_id == 0:
            session_text = " with no session (unlinked)"
            
        await message.answer(
            f"✅ Category '{category_name}' updated successfully{session_text}!", 
            reply_markup=keyboard
        )
    else:
        await message.answer("❌ Error updating the category.")
    
    await state.clear()

@router.callback_query(F.data == "add_channel", F.from_user.id == ADMIN_ID)
async def add_channel_start(call: types.CallbackQuery, state: FSMContext):
    """
    start the process of adding a channel
    """
    await call.message.answer("Enter a channel link in the format 'https://t.me/username':")
    await state.set_state(AddChannelStates.waiting_for_channel_link)
    await call.answer()

@router.message(AddChannelStates.waiting_for_channel_link, F.text, F.from_user.id == ADMIN_ID)
async def process_channel_link(message: types.Message, state: FSMContext, channels_data: dict):
    """
    get a channel link from the user
    """
    channel_link = message.text.strip()
    # check if the entered string is a link
    if channel_link.startswith("https://t.me/"):
        # check if the channel already exists
        for channel_id, data in channels_data.items():
            if data.get('Invite_link') == channel_link:
                await message.answer("A channel with this link already exists. Enter another link:")
                return
                
        await state.update_data(channel_link=channel_link)
        await message.answer("Enter a channel name:")
        await state.set_state(AddChannelStates.waiting_for_channel_name)
    else:
        await message.answer("Incorrect channel link. Enter a link in the format 'https://t.me/username':")

@router.message(AddChannelStates.waiting_for_channel_name, F.text, F.from_user.id == ADMIN_ID)
async def process_channel_name(message: types.Message, state: FSMContext, channels_data: dict):
    """
    get a channel name from the user
    """
    channel_name = message.text
    await state.update_data(channel_name=channel_name)
    
    # Get categories with session info
    @sync_to_async
    def get_ordered_categories_with_session():
        return list(Category.objects.select_related('session').all().order_by('id'))
    
    categories = await get_ordered_categories_with_session()
    
    if not categories:
        await message.answer("No categories found. Please add a category first.")
        await state.clear()
        return
    
    # Create mapping of display indices to actual category IDs
    category_mapping = {}
    categories_text = "Select a category from the list (number: Category Name):\n"
    
    for idx, category in enumerate(categories, 1):
        category_mapping[idx] = category.id
        session_info = f" (Session: {category.session.phone})" if category.session else ""
        categories_text += f"{idx}: {category.name}{session_info}\n"
    
    # Store the mapping in the state
    await state.update_data(category_mapping=category_mapping)
    
    await message.answer(categories_text)
    await state.set_state(AddChannelStates.waiting_for_channel_category)

@router.message(AddChannelStates.waiting_for_channel_category, F.text, F.from_user.id == ADMIN_ID)
async def process_channel_category(message: types.Message, state: FSMContext, channels_data: dict):
    """
    get the channel category and save the data
    """
    user_data = await state.get_data()
    category_mapping = user_data.get('category_mapping', {})
    
    try:
        display_index = int(message.text)
        # Get the actual category ID from the mapping
        if display_index in category_mapping:
            category_id = category_mapping[display_index]
        else:
            await message.answer("Invalid category number. Please enter a number from the list.")
            return
    except ValueError:
        await message.answer("The category number must be a number. Try again.")
        return
        
    # check if the category exists
    @sync_to_async
    def check_category_exists(category_id):
        try:
            return Category.objects.get(id=category_id)
        except Category.DoesNotExist:
            return None
            
    category = await check_category_exists(category_id)
    if not category:
        await message.answer("Category not found. Try again.")
        return

    # save category information in the state
    await state.update_data(category_id=category_id)

    # Get available sessions for selection
    @sync_to_async
    def get_active_sessions():
        try:
            # Try to filter active sessions
            try:
                # Safely handle fields that might be missing
                return list(TelegramSession.objects.filter(is_active=True).order_by('phone'))
            except Exception as field_error:
                logger.error(f"Error filtering active sessions: {field_error}")
                # Fallback to all sessions
                return list(TelegramSession.objects.all().order_by('phone'))
        except Exception as e:
            logger.error(f"Error fetching sessions: {e}")
            return []
    
    sessions = await get_active_sessions()
    
    if sessions:
        # Create mapping of display indices to actual session IDs
        session_mapping = {}
        sessions_text = "Select a Telegram session for this channel (enter number, or 0 to skip):\n"
        
        for idx, session in enumerate(sessions, 1):
            session_mapping[idx] = session.id
            sessions_text += f"{idx}: {session.phone}\n"
        
        # Store the mapping in the state
        await state.update_data(session_mapping=session_mapping)
        
        await message.answer(sessions_text)
        await state.set_state(AddChannelStates.waiting_for_channel_session)
    else:
        # If no sessions, skip to channel creation
        await message.answer("No active sessions found. The channel will use the default session.")
        await create_channel_with_data(message, state, channels_data, None)

@router.message(AddChannelStates.waiting_for_channel_session, F.text, F.from_user.id == ADMIN_ID)
async def process_channel_session(message: types.Message, state: FSMContext, channels_data: dict):
    """
    get the channel session and save the data
    """
    user_data = await state.get_data()
    session_mapping = user_data.get('session_mapping', {})
    
    # Skip if user enters 0
    if message.text == "0":
        await create_channel_with_data(message, state, channels_data, None)
        return
    
    # Validate the session index
    try:
        display_index = int(message.text)
        # Get the actual session ID from the mapping
        if display_index in session_mapping:
            session_id = session_mapping[display_index]
        else:
            await message.answer("Invalid session number. Please enter a number from the list or type 0 to skip.")
            return
    except ValueError:
        await message.answer("The session number must be a number. Please try again (or type 0 to skip).")
        return
    
    # Check if session exists
    @sync_to_async
    def check_session_exists(session_id):
        try:
            return TelegramSession.objects.get(id=session_id, is_active=True)
        except TelegramSession.DoesNotExist:
            return None
    
    session = await check_session_exists(session_id)
    if not session:
        await message.answer("Session not found or inactive. Please try again (or type 0 to skip).")
        return
    
    # Create the channel with the selected session
    await create_channel_with_data(message, state, channels_data, session_id)

async def create_channel_with_data(message: types.Message, state: FSMContext, channels_data: dict, session_id=None):
    """
    Create a new channel with the collected data
    """
    # Get data from state
    user_data = await state.get_data()
    channel_link = user_data.get('channel_link')
    channel_name = user_data.get('channel_name')
    category_id = user_data.get('category_id')
    
    # Create the channel in the database
    @sync_to_async
    def create_channel_in_db(name, url, category_id, session_id):
        try:
            channel_data = {
                'name': name,
                'url': url,
                'category_id': category_id,
                'is_active': True
            }
            
            if session_id:
                channel_data['session_id'] = session_id
                
            channel = Channel.objects.create(**channel_data)
            
            category = Category.objects.get(id=category_id)
            session_info = ""
            if session_id:
                session = TelegramSession.objects.get(id=session_id)
                session_info = f" with session {session.phone}"
                
            logger.info(f"Created a new channel: ID {channel.id}, name '{name}', category '{category.name}'{session_info}")
            return channel, category, session_info
        except Exception as e:
            logger.error(f"Error creating the channel '{name}': {e}")
            return None, None, ""

    # Get channels with session preloaded for keyboard
    @sync_to_async
    def get_all_channels_with_session():
        try:
            # Try with select_related including session
            try:
                return list(Channel.objects.select_related('session').all())
            except Exception as e:
                logger.error(f"Error fetching channels with sessions: {e}")
                # Fallback without select_related
                return list(Channel.objects.all())
        except Exception as e:
            logger.error(f"Error fetching channels: {e}")
            return []

    result = await create_channel_in_db(channel_name, channel_link, category_id, session_id)
    channel, category, session_info = result
    
    if channel:
        # get all channels to update the keyboard - now using the function that preloads sessions
        channels = await get_all_channels_with_session()
        
        success_message = f"✅ Channel '{channel_name}' has been added to category '{category.name}'{session_info}"
        
        # Use prepare_channels_keyboard for async safety
        keyboard = await prepare_channels_keyboard(channels)
        await message.answer(success_message, reply_markup=keyboard)
    else:
        await message.answer("❌ Error adding the channel.")
    
    await state.clear()

async def prepare_channels_keyboard(channels, category_id=None):
    """
    Prepare the channels keyboard in an async-safe way
    """
    keyboard = await sync_to_async(get_channels_keyboard)(channels, category_id)
    return keyboard

@router.callback_query(F.data == "remove_channel", F.from_user.id == ADMIN_ID)
async def remove_channel_start(call: types.CallbackQuery, state: FSMContext):
    """
    start the process of deleting a channel
    """
    # Get all channels with sessions
    @sync_to_async
    def get_channels_with_sessions():
        return list(Channel.objects.select_related('session', 'category').all().order_by('id'))
    
    channels = await get_channels_with_sessions()
    
    if not channels:
        await call.message.answer("No channels found to delete.")
        return
    
    # Create mapping of display indices to actual channel IDs
    channel_mapping = {}
    channels_text = "Enter the number of the channel to delete:\n"
    
    for idx, channel in enumerate(channels, 1):
        channel_mapping[idx] = channel.id
        status = "✅" if channel.is_active else "❌"
        category_info = f" - Category: {channel.category.name}" if channel.category else ""
        session_info = f" - Session: {channel.session.phone}" if channel.session else ""
        channels_text += f"{idx}: {status} {channel.name}{category_info}{session_info}\n"
    
    # Store the mapping in the state
    await state.update_data(channel_mapping=channel_mapping)
    
    await call.message.answer(channels_text)
    await state.set_state(RemoveChannelState.waiting_for_input)
    await call.answer()

@router.message(RemoveChannelState.waiting_for_input, F.text, F.from_user.id == ADMIN_ID)
async def process_remove_channel_input(message: types.Message, state: FSMContext):
    """
    process the user's input for deleting a channel
    """
    user_data = await state.get_data()
    channel_mapping = user_data.get('channel_mapping', {})
    
    try:
        display_index = int(message.text.strip())
        # Get the actual channel ID from the mapping
        if display_index in channel_mapping:
            channel_id = channel_mapping[display_index]
        else:
            await message.answer("Invalid channel number. Please enter a number from the list.")
            return
    except ValueError:
        await message.answer("Please enter a valid channel number.")
        return
    
    # find and delete the channel
    @sync_to_async
    def find_and_delete_channel(channel_id):
        try:
            channel = Channel.objects.get(id=channel_id)
            channel_name = channel.name
            channel.delete()
            logger.info(f"Deleted channel #{channel_id} '{channel_name}'")
            return channel_name, True
        except Channel.DoesNotExist:
            logger.warning(f"Tried to delete a non-existent channel with ID {channel_id}")
            return None, False
        except Exception as e:
            logger.error(f"Error deleting the channel with ID {channel_id}: {e}")
            return None, False
    
    channel_name, success = await find_and_delete_channel(channel_id)
    
    if not success:
        await message.answer(f"❌ Channel not found or error occurred.")
        return
    
    # get the updated list of channels
    @sync_to_async
    def get_all_channels_with_session():
        try:
            # Try with select_related including session
            try:
                return list(Channel.objects.select_related('session').all())
            except Exception as e:
                logger.error(f"Error fetching channels with sessions: {e}")
                # Fallback without select_related
                return list(Channel.objects.all())
        except Exception as e:
            logger.error(f"Error fetching channels: {e}")
            return []
    
    channels = await get_all_channels_with_session()
    keyboard = await prepare_channels_keyboard(channels)
    
    await message.answer(
        f"✅ Channel '{channel_name}' has been deleted!",
        reply_markup=keyboard
    )
    
    await state.clear()

@router.callback_query(F.data == "add_category", F.from_user.id == ADMIN_ID)
async def add_category_start(call: types.CallbackQuery, state: FSMContext):
    """
    start the process of adding a category
    """
    await call.message.answer("Enter the name of the new category:")
    await state.set_state(AddCategoryStates.waiting_for_category_name)
    await call.answer()

@router.message(AddCategoryStates.waiting_for_category_name, F.text, F.from_user.id == ADMIN_ID)
async def process_category_name(message: types.Message, state: FSMContext, channels_data: dict, bot: Bot):
    """
    get a category name from the user and proceed to session selection
    """
    category_name = message.text
    await state.update_data(category_name=category_name)
    
    # Get available sessions for selection
    @sync_to_async
    def get_active_sessions():
        return list(TelegramSession.objects.filter(is_active=True).order_by('phone'))
        
    sessions = await get_active_sessions()
    
    if sessions:
        # Create mapping of display indices to actual session IDs
        session_mapping = {}
        sessions_text = "Select a Telegram session for this category (enter number, or 0 to skip):\n"
        
        for idx, session in enumerate(sessions, 1):
            session_mapping[idx] = session.id
            sessions_text += f"{idx}: {session.phone}\n"
        
        # Store the mapping in the state
        await state.update_data(session_mapping=session_mapping)
        
        await message.answer(sessions_text)
        await state.set_state(AddCategoryStates.waiting_for_category_session)
    else:
        # If no sessions, create category without session
        await message.answer("No active sessions found. The category will not be linked to any session.")
        await create_category_with_data(message, state, channels_data, None)

@router.message(AddCategoryStates.waiting_for_category_session, F.text, F.from_user.id == ADMIN_ID)
async def process_category_session(message: types.Message, state: FSMContext, channels_data: dict, bot: Bot):
    """
    get the category session and save the data
    """
    user_data = await state.get_data()
    session_mapping = user_data.get('session_mapping', {})
    
    # Skip if user enters 0
    if message.text == "0":
        await create_category_with_data(message, state, channels_data, None)
        return
    
    # Validate the session index
    try:
        display_index = int(message.text)
        # Get the actual session ID from the mapping
        if display_index in session_mapping:
            session_id = session_mapping[display_index]
        else:
            await message.answer("Invalid session number. Please enter a number from the list or type 0 to skip.")
            return
    except ValueError:
        await message.answer("The session number must be a number. Please try again (or type 0 to skip).")
        return
    
    # Check if session exists
    @sync_to_async
    def check_session_exists(session_id):
        try:
            return TelegramSession.objects.get(id=session_id, is_active=True)
        except TelegramSession.DoesNotExist:
            return None
    
    session = await check_session_exists(session_id)
    if not session:
        await message.answer("Session not found or inactive. Please try again (or type 0 to skip).")
        return
    
    # Create the category with the selected session
    await create_category_with_data(message, state, channels_data, session_id)

async def create_category_with_data(message: types.Message, state: FSMContext, channels_data: dict, session_id=None):
    """
    Create a new category with the collected data
    """
    # Get data from state
    user_data = await state.get_data()
    category_name = user_data.get('category_name')
    
    # Create the category in the database
    @sync_to_async
    def create_category_in_db(name, session_id):
        try:
            category_data = {
                'name': name
            }
            
            if session_id:
                category_data['session_id'] = session_id
                
            category = Category.objects.create(**category_data)
            
            session_info = ""
            if session_id:
                session = TelegramSession.objects.get(id=session_id)
                session_info = f" with session {session.phone}"
                
            logger.info(f"Created a new category: ID {category.id}, name '{name}'{session_info}")
            return category.id, session_info
        except Exception as e:
            logger.error(f"Error creating the category '{name}': {e}")
            return None, ""

    result = await create_category_in_db(category_name, session_id)
    new_category_id, session_info = result
    
    if new_category_id:
        # Get updated categories list with sessions
        @sync_to_async
        def get_ordered_categories_with_session():
            return list(Category.objects.select_related('session').all().order_by('id'))
        
        categories = await get_ordered_categories_with_session()
        keyboard = await prepare_categories_keyboard(channels_data, categories)
        
        success_message = f"✅ The category '{category_name}' (ID: {new_category_id}) has been added{session_info}."
        await message.answer(success_message, reply_markup=keyboard)
        await state.clear()
        
        # notify about changes
        await message.answer("The category has been added successfully, changes saved.", reply_markup=main_menu_keyboard)
    else:
        await message.answer("❌ Error adding the category.")
        await state.clear()

@router.callback_query(F.data == "remove_category", F.from_user.id == ADMIN_ID)
async def remove_category_start(call: types.CallbackQuery, state: FSMContext, channels_data: dict):
    """
    start the process of deleting a category
    """
    # Get categories with session info
    @sync_to_async
    def get_ordered_categories_with_session():
        return list(Category.objects.select_related('session').all().order_by('id'))
    
    categories = await get_ordered_categories_with_session()
    
    if not categories:
        await call.message.answer("No categories found to delete.")
        return
    
    # Create mapping of display indices to actual category IDs
    category_mapping = {}
    categories_text = "Select the number of the category to delete:\n"
    
    for idx, category in enumerate(categories, 1):
        category_mapping[idx] = category.id
        session_info = f" (Session: {category.session.phone})" if category.session else ""
        categories_text += f"{idx}: {category.name}{session_info}\n"
    
    # Store the mapping in the state
    await state.update_data(category_mapping=category_mapping)
    
    await call.message.answer(categories_text)
    await state.set_state(RemoveCategoryStates.waiting_for_category_id)
    await call.answer()

@router.message(RemoveCategoryStates.waiting_for_category_id, F.text, F.from_user.id == ADMIN_ID)
async def process_remove_category_id(message: types.Message, state: FSMContext, channels_data: dict, bot: Bot):
    """
    get a category ID from the user and delete it
    """
    user_data = await state.get_data()
    category_mapping = user_data.get('category_mapping', {})
    
    try:
        display_index = int(message.text)
        # Get the actual category ID from the mapping
        if display_index in category_mapping:
            category_id = category_mapping[display_index]
        else:
            await message.answer("Invalid category number. Please enter a number from the list.")
            return
    except ValueError:
        await message.answer("Please enter a valid category number.")
        return
    
    # Get and delete the category
    @sync_to_async
    def delete_category_and_update_references(category_id):
        try:
            category = Category.objects.get(id=category_id)
            category_name = category.name
            
            # Get all channels using this category
            related_channels = list(Channel.objects.filter(category_id=category_id))
            
            # Delete the category
            category.delete()
            
            # Update channels to remove the deleted category reference
            for channel in related_channels:
                channel.category = None
                channel.save()
                
            logger.info(f"Deleted category: ID {category_id}, name '{category_name}'")
            logger.info(f"Updated {len(related_channels)} channels to remove deleted category reference")
            
            return category_name, True
        except Category.DoesNotExist:
            logger.warning(f"Tried to delete a non-existent category with ID {category_id}")
            return None, False
        except Exception as e:
            logger.error(f"Error deleting category #{category_id}: {e}")
            return None, False
    
    category_name, success = await delete_category_and_update_references(category_id)
    
    if not success:
        await message.answer("There is no category with this ID or an error occurred.")
        return
    
    # Get updated categories list with sessions
    @sync_to_async
    def get_ordered_categories_with_session():
        return list(Category.objects.select_related('session').all().order_by('id'))
    
    categories = await get_ordered_categories_with_session()
    keyboard = await prepare_categories_keyboard(channels_data, categories)

    await message.answer(f"The category '{category_name}' has been deleted.", reply_markup=keyboard)
    await state.clear()

    # notify about changes
    await message.answer("The category has been deleted successfully, changes saved.", reply_markup=main_menu_keyboard)

# example of a simple admin command (for checking the bot's functionality)
@router.message(Command("ping"), F.from_user.id == ADMIN_ID)
async def admin_ping(message: types.Message):
    await message.answer("Pong!")

# add the /stop command for stopping the bot
@router.message(Command("stop"), F.from_user.id == ADMIN_ID)
async def cmd_stop(message: types.Message, bot: Bot):
    await message.answer("Stopping the bot...")
    # use gradual shutdown
    from main import stop_event, dp
    stop_event.set()
    await message.answer("The bot has been stopped successfully!")
    await bot.session.close()

def is_admin(user_id: int) -> bool:
    return user_id == ADMIN_ID

# Only allow admin to use these commands
@router.message(F.from_user.id == ADMIN_ID, Command("link_session"))
async def cmd_link_session(message: types.Message, state: FSMContext):
    """Command to link a session to a channel or category"""
    # Get all channels
    @sync_to_async
    def get_channels():
        return list(Channel.objects.select_related('session').all().order_by('name'))
    
    channels = await get_channels()
    
    if not channels:
        await message.answer("No channels found. Please add channels first.")
        return
    
    # Prepare keyboard with async-safe method
    keyboard = await prepare_channels_keyboard(channels)
    
    await message.answer(
        "Select a channel to link to a session:",
        reply_markup=keyboard
    )
    
    await state.set_state(SessionLinkStates.waiting_for_channel)

@router.callback_query(SessionLinkStates.waiting_for_channel, F.data.startswith("channel_"))
async def select_channel_for_link(callback: types.CallbackQuery, state: FSMContext):
    """Handler for channel selection for session linking"""
    channel_id = callback.data.split("_")[1]
    
    # Get all active sessions
    @sync_to_async
    def get_sessions():
        return list(TelegramSession.objects.filter(is_active=True).order_by('phone'))
    
    sessions = await get_sessions()
    
    if not sessions:
        back_button = await prepare_back_button()
        await callback.message.edit_text(
            "No active sessions found. Please add and activate sessions first.",
            reply_markup=back_button
        )
        await state.clear()
        return
    
    # Create mapping of display indices to actual session IDs
    session_mapping = {}
    
    # Create keyboard with sessions
    @sync_to_async
    def create_sessions_keyboard():
        keyboard = []
        for idx, session in enumerate(sessions, 1):
            session_mapping[idx] = session.id
            keyboard.append([
                {"text": f"{idx}: {session.phone}", "callback_data": f"session_{session.id}_{channel_id}"}
            ])
        
        # Add option to unlink session
        keyboard.append([{"text": "❌ Unlink session", "callback_data": f"unlink_session_{channel_id}"}])
        
        # Add back button
        keyboard.append([{"text": "⬅️ Back", "callback_data": "back"}])
        return {"inline_keyboard": keyboard}
    
    # Store channel_id in state
    await state.update_data(channel_id=channel_id)
    await state.update_data(session_mapping=session_mapping)
    
    # Get channel info
    @sync_to_async
    def get_channel_info(channel_id):
        channel = Channel.objects.select_related('session').get(id=channel_id)
        return {
            'name': channel.name,
            'session': channel.session.phone if channel.session else None
        }
    
    channel_info = await get_channel_info(channel_id)
    keyboard = await create_sessions_keyboard()
    
    current_session = ""
    if channel_info['session']:
        current_session = f"\nCurrently linked to: {channel_info['session']}"
    
    await callback.message.edit_text(
        f"Select a session to link to channel '{channel_info['name']}'{current_session}:",
        reply_markup=keyboard
    )
    
    await state.set_state(SessionLinkStates.waiting_for_session)

async def prepare_back_button():
    """
    Prepare the back button in an async-safe way
    """
    @sync_to_async
    def create_button():
        return get_back_button()
    
    return await create_button()

@router.callback_query(SessionLinkStates.waiting_for_session, F.data.startswith("session_"))
async def link_session_to_channel(callback: types.CallbackQuery, state: FSMContext):
    """Handler for session selection and linking to channel"""
    # Parse session_id and channel_id from callback data
    parts = callback.data.split("_")
    session_id = parts[1]
    channel_id = parts[2]
    
    # Link session to channel
    @sync_to_async
    def update_channel_session(channel_id, session_id):
        channel = Channel.objects.get(id=channel_id)
        session = TelegramSession.objects.get(id=session_id)
        channel.session = session
        channel.save()
        return {
            'channel_name': channel.name,
            'session_phone': session.phone
        }
    
    result = await update_channel_session(channel_id, session_id)
    back_button = await prepare_back_button()
    
    await callback.message.edit_text(
        f"✅ Successfully linked session {result['session_phone']} to channel {result['channel_name']}.",
        reply_markup=back_button
    )
    
    await state.clear()

@router.callback_query(SessionLinkStates.waiting_for_session, F.data.startswith("unlink_session_"))
async def unlink_session_from_channel(callback: types.CallbackQuery, state: FSMContext):
    """Handler for unlinking session from channel"""
    # Parse channel_id from callback data
    channel_id = callback.data.split("_")[2]
    
    # Unlink session from channel
    @sync_to_async
    def remove_channel_session(channel_id):
        channel = Channel.objects.get(id=channel_id)
        channel.session = None
        channel.save()
        return channel.name
    
    channel_name = await remove_channel_session(channel_id)
    back_button = await prepare_back_button()
    
    await callback.message.edit_text(
        f"✅ Successfully unlinked session from channel {channel_name}.",
        reply_markup=back_button
    )
    
    await state.clear()

# Command to link session to category
@router.message(F.from_user.id == ADMIN_ID, Command("link_category"))
async def cmd_link_category(message: types.Message, state: FSMContext):
    """Command to link a session to a category"""
    # Get all categories
    @sync_to_async
    def get_categories():
        return list(Category.objects.select_related('session').all().order_by('name'))
    
    categories = await get_categories()
    
    if not categories:
        await message.answer("No categories found. Please add categories first.")
        return
    
    # Create keyboard with async-safe method
    keyboard = await prepare_categories_keyboard(None, categories)
    
    await message.answer(
        "Select a category to link to a session:",
        reply_markup=keyboard
    )
    
    await state.set_state(SessionLinkStates.waiting_for_category)

@router.callback_query(SessionLinkStates.waiting_for_category, F.data.startswith("category_"))
async def select_category_for_link(callback: types.CallbackQuery, state: FSMContext):
    """Handler for category selection for session linking"""
    category_id = callback.data.split("_")[1]
    
    # Get all active sessions
    @sync_to_async
    def get_sessions():
        return list(TelegramSession.objects.filter(is_active=True).order_by('phone'))
    
    sessions = await get_sessions()
    
    if not sessions:
        back_button = await prepare_back_button()
        await callback.message.edit_text(
            "No active sessions found. Please add and activate sessions first.",
            reply_markup=back_button
        )
        await state.clear()
        return
    
    # Create mapping of display indices to actual session IDs
    session_mapping = {}
    
    # Create keyboard with sessions
    @sync_to_async
    def create_sessions_keyboard():
        keyboard = []
        for idx, session in enumerate(sessions, 1):
            session_mapping[idx] = session.id
            keyboard.append([
                {"text": f"{idx}: {session.phone}", "callback_data": f"cat_session_{session.id}_{category_id}"}
            ])
        
        # Add option to unlink session
        keyboard.append([{"text": "❌ Unlink session", "callback_data": f"unlink_cat_session_{category_id}"}])
        
        # Add back button
        keyboard.append([{"text": "⬅️ Back", "callback_data": "back"}])
        return {"inline_keyboard": keyboard}
    
    # Store category_id and session mapping in state
    await state.update_data(category_id=category_id)
    await state.update_data(session_mapping=session_mapping)
    
    # Get category info
    @sync_to_async
    def get_category_info(category_id):
        category = Category.objects.select_related('session').get(id=category_id)
        return {
            'name': category.name,
            'session': category.session.phone if category.session else None
        }
    
    category_info = await get_category_info(category_id)
    keyboard = await create_sessions_keyboard()
    
    current_session = ""
    if category_info['session']:
        current_session = f"\nCurrently linked to: {category_info['session']}"
    
    await callback.message.edit_text(
        f"Select a session to link to category '{category_info['name']}'{current_session}:",
        reply_markup=keyboard
    )
    
    await state.set_state(SessionLinkStates.waiting_for_session)

@router.callback_query(SessionLinkStates.waiting_for_session, F.data.startswith("cat_session_"))
async def link_session_to_category(callback: types.CallbackQuery, state: FSMContext):
    """Handler for session selection and linking to category"""
    # Parse session_id and category_id from callback data
    parts = callback.data.split("_")
    session_id = parts[2]
    category_id = parts[3]
    
    # Link session to category
    @sync_to_async
    def update_category_session(category_id, session_id):
        category = Category.objects.get(id=category_id)
        session = TelegramSession.objects.get(id=session_id)
        category.session = session
        category.save()
        return {
            'category_name': category.name,
            'session_phone': session.phone
        }
    
    result = await update_category_session(category_id, session_id)
    back_button = await prepare_back_button()
    
    await callback.message.edit_text(
        f"✅ Successfully linked session {result['session_phone']} to category {result['category_name']}.",
        reply_markup=back_button
    )
    
    await state.clear()

@router.callback_query(SessionLinkStates.waiting_for_session, F.data.startswith("unlink_cat_session_"))
async def unlink_session_from_category(callback: types.CallbackQuery, state: FSMContext):
    """Handler for unlinking session from category"""
    # Parse category_id from callback data
    category_id = callback.data.split("_")[3]
    
    # Unlink session from category
    @sync_to_async
    def remove_category_session(category_id):
        category = Category.objects.get(id=category_id)
        category.session = None
        category.save()
        return category.name
    
    category_name = await remove_category_session(category_id)
    back_button = await prepare_back_button()
    
    await callback.message.edit_text(
        f"✅ Successfully unlinked session from category {category_name}.",
        reply_markup=back_button
    )
    
    await state.clear()

async def prepare_categories_keyboard(channels_data, categories):
    """
    Prepare the categories keyboard in an async-safe way
    """
    keyboard = await sync_to_async(get_categories_keyboard)(channels_data, categories)
    return keyboard