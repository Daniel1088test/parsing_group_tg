import os

# Telegram bot configuration
API_HASH = "c839f28bad345082329ec086fca021fa"  # API hash
API_ID = "19840544"  # API id
TOKEN_BOT = "7923260865:AAGWm7t0Zz2PqFPI5PldEVwrOC4HZ_5oP0c"  # Bot token
ADMIN_ID = 574349489  # Admin ID
BOT_USERNAME = "@Channels_hunt_bot"

# File paths
FILE_JSON = 'file.json'  # Channel data file
CATEGORIES_JSON = 'categories.json'  # Categories file

# Message limits
MAX_MESSAGES = 100000

# Server configuration
WEB_SERVER_HOST = "127.0.0.1"  # Internal server host
WEB_SERVER_PORT = 8000  # Internal server port
WEB_SERVER_HOST2 = "108.181.154.114"

# Public URL for the bot
PUBLIC_URL = os.getenv('PUBLIC_URL', 'https://parsinggrouptg-production.up.railway.app')
if not PUBLIC_URL.startswith('http'):
    PUBLIC_URL = f"https://{PUBLIC_URL}"

# Security configuration
SECRET_KEY = os.getenv('SECRET_KEY', '/QoXhzTJkyhzSKccxR+XV0pf4T2zqLfXzPlSwegi6Cs=')
ADMIN_USERNAME = 'DAndy'
ADMIN_PASSWORD = 'Remoreid19976'

# Directory structure
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_FOLDER = os.path.join(BASE_DIR, 'data')
MESSAGES_FOLDER = os.path.join(DATA_FOLDER, 'messages')
SESSIONS_DIR = os.path.join(DATA_FOLDER, 'sessions')

# Create necessary directories
for directory in [DATA_FOLDER, MESSAGES_FOLDER, SESSIONS_DIR]:
    os.makedirs(directory, exist_ok=True)

# Database configuration (from Railway)
DATABASE_URL = os.getenv('DATABASE_URL', 'postgresql://postgres:urCNhXdwvbqOvvEsJDffIiDUMcLhAvcs@switchback.proxy.rlwy.net:10052/railway')
