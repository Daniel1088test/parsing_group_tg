from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage
from tg_bot.config import TOKEN_BOT

# Initialize bot and dispatcher
bot = Bot(token=TOKEN_BOT)
storage = MemoryStorage()
dp = Dispatcher(storage=storage)

# This will be imported by other modules
__all__ = ["bot", "dp"] 