from .common import router as common_router
from .admin import router as admin_router
from .session_handlers import router as session_router

__all__ = ['common_router', 'admin_router', 'session_router']