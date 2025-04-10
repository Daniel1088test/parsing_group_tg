from telethon import TelegramClient
from tg_bot.config import API_ID, API_HASH

# global variable for storing Telethon client
client = None

async def get_telegram_client():
    global client
    if client is None:
        client = TelegramClient('anon', API_ID, API_HASH)
        await client.start()
    return client