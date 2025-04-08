from tg_bot.handlers.common import router as common_router
from tg_bot.handlers.admin import admin_router
from tg_bot.handlers.session import session_router
from tg_bot.handlers.session_buttons import session_buttons_router
from tg_bot.handlers.menu_buttons import menu_buttons_router
from tg_bot.handlers.fallback import fallback_router

__all__ = ['common_router', 'admin_router', 'session_router', 'session_buttons_router', 'menu_buttons_router', 'fallback_router']