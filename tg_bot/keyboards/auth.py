from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

def get_auth_button(website_url):
    """
    Create an inline keyboard with a button to authenticate Telethon.
    
    Parameters:
    -----------
    website_url (str): URL of the website
    
    Returns:
    --------
    InlineKeyboardMarkup: Keyboard with an auth button
    """
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔐 Authorize Telethon", url=f"{website_url}/admin-panel/auth-telethon/")],
    ])
    
    return keyboard 