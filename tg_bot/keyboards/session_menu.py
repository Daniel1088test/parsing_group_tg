from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton

session_menu_keyboard = ReplyKeyboardMarkup(
    keyboard=[
        [
            KeyboardButton(text="➕ Add new session"),
        ],
        [
            KeyboardButton(text="📋 List of sessions"),
        ],
        [
            KeyboardButton(text="🔐 Authorize Telethon"),
        ],
        [
            KeyboardButton(text="🔙 Back to main menu")
        ]
    ],
    resize_keyboard=True,
    one_time_keyboard=False,
    input_field_placeholder="Select an option..."
)

def get_sessions_list_keyboard(sessions):
    """
    create an inline keyboard with a list of sessions
    
    Args:
        sessions: list of TelegramSession objects
        
    Returns:
        InlineKeyboardMarkup: keyboard with buttons for each session
    """
    keyboard = []
    for session in sessions:
        status = "✅" if session.is_active else "❌"
        keyboard.append([
            InlineKeyboardButton(
                text=f"{status} {session.phone}",
                callback_data=f"session_{session.id}"
            )
        ])
    keyboard.append([InlineKeyboardButton(text="🔙 Back", callback_data="back_to_session_menu")])
    return InlineKeyboardMarkup(inline_keyboard=keyboard)

def get_session_actions_keyboard(session_id):
    """
    create an inline keyboard with actions for a session
    
    Args:
        session_id: session ID
        
    Returns:
        InlineKeyboardMarkup: keyboard with action buttons
    """
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="✏️ Edit", callback_data=f"edit_session_{session_id}"),
                InlineKeyboardButton(text="🗑 Delete", callback_data=f"delete_session_{session_id}")
            ],
            [
                InlineKeyboardButton(text="🔙 Back", callback_data="back_to_sessions_list")
            ]
        ]
    ) 