from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

def get_auth_button(website_url):
    """
    Create keyboard with button to authorize Telethon through website
    
    Args:
        website_url (str): URL of the website
        
    Returns:
        InlineKeyboardMarkup: The keyboard markup
    """
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔐 Authorize Telethon", url=f"{website_url}/admin/auth/telethon/")],
        [InlineKeyboardButton(text="🔙 Back", callback_data="back_to_main")]
    ]) 