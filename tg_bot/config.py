import os
from pathlib import Path

# Telegram API credentials
API_ID = os.getenv('API_ID', '19840544')
API_HASH = os.getenv('API_HASH', 'c839f28bad345082329ec086fca021fa')

# Telegram Bot token
TOKEN_BOT = os.getenv('TOKEN_BOT', '7923260865:AAGWm7t0Zz2PqFPI5PldEVwrOC4HZ_5oP0c')

# Admin ID - можна вказати декілька ID через кому
# ID користувача в кадрі: 574349489, додамо новий ID
ADMIN_IDS = list(map(str.strip, os.getenv('ADMIN_ID', '574349489,1088968819,3156523012').split(',')))
ADMIN_ID = ADMIN_IDS[0]  # Для сумісності зі старим кодом

# Base project path
BASE_DIR = Path(__file__).resolve().parent.parent

# Server configuration
WEB_SERVER_HOST = os.getenv('WEB_SERVER_HOST', '0.0.0.0')
WEB_SERVER_PORT = int(os.getenv('PORT', 8080))

# Get Public URL for webhooks or redirect, falling back to localhost
PUBLIC_URL = os.getenv(
    'PUBLIC_URL', 
    os.getenv('RAILWAY_STATIC_URL', 'http://localhost:8080')
)

# Path to data storage
DATA_FOLDER = os.path.join(BASE_DIR, 'data')
MESSAGES_FOLDER = os.path.join(DATA_FOLDER, 'messages')

# Create folders if they don't exist
os.makedirs(DATA_FOLDER, exist_ok=True)
os.makedirs(MESSAGES_FOLDER, exist_ok=True)

# Files paths
FILE_JSON = os.path.join(DATA_FOLDER, 'data.json')
CATEGORIES_JSON = os.path.join(DATA_FOLDER, 'categories.json')

# Maximum messages to parse per channel
MAX_MESSAGES = int(os.getenv('MAX_MESSAGES', 10))

# Session file name
TELETHON_SESSION = 'telethon_session'

# Django secret key
SECRET_KEY = os.getenv(
    'SECRET_KEY', 
    'django-insecure-+0y690!*z(#c)1a%r8&wasr(%33csshyjoc#vflcg3!_z0c2#&'
) 