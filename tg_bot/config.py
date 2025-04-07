import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Telethon settings
# Get values from environment first, then fall back to hardcoded values if they exist
API_ID_STR = os.getenv("API_ID", "19840544") 
API_ID = int(API_ID_STR)  # Make sure API_ID is an integer
API_HASH = os.getenv("API_HASH", "c839f28bad345082329ec086fca021fa")  # Use actual default API_HASH
SESSION_NAME = os.getenv("SESSION_NAME", "telethon_session")
TOKEN_BOT = os.getenv("BOT_TOKEN", "7923260865:AAGWm7t0Zz2PqFPI5PldEVwrOC4HZ_5oP0c")  # Get from env or use default
ADMIN_ID = int(os.getenv("ADMIN_ID", "574349489"))  # ID адміністратора у форматі числа!
BOT_USERNAME = os.getenv("BOT_USERNAME", "@Channels_hunt_bot")
# Путь к файлу с данными о каналах
FILE_JSON = 'file.json'

#yoi=20662346
#yoi=8981176be8754bcd6dbfdb4d9f499b57

# Путь к файлу с категориями
CATEGORIES_JSON = 'categories.json'

# Максимальное количество сообщений в папке data
MAX_MESSAGES = 100000

# Get web server configuration from environment variables with fallbacks
WEB_SERVER_HOST = os.getenv("WEB_SERVER_HOST", "0.0.0.0")
# Fix parsing of WEB_SERVER_PORT to handle empty strings
port_str = os.getenv("WEB_SERVER_PORT", "8000")
WEB_SERVER_PORT = int(port_str) if port_str else 8000

# For URLs shown to users - use the Railway domain if available
PUBLIC_HOST = os.getenv("PUBLIC_HOST", "parsinggrouptg-production.up.railway.app")

SECRET_KEY = os.getenv("SECRET_KEY", '/QoXhzTJkyhzSKccxR+XV0pf4T2zqLfXzPlSwegi6Cs=')
ADMIN_USERNAME = os.getenv("ADMIN_USERNAME", 'DAndy')
ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD", 'Remoreid19976')


# Папки
BASE_DIR = os.path.dirname(__file__)
DATA_FOLDER = os.path.join(BASE_DIR, 'data')
MESSAGES_FOLDER = os.path.join(DATA_FOLDER, 'messages')
