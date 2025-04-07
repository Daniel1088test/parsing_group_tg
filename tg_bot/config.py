# import os
# API_HASH = "8981176be8754bcd6dbfdb4d9f499b57"  # Замените на свой API hash!
# API_ID = "20662346"  # Замените на свой API id!
# TOKEN_BOT = "7896267673:AAFkPv6ro2aIBnlTgXOmzEKVvLo6TRbw-xI"  # Замените на токен своего бота!
# ADMIN_ID = 7265248372  # Замените на свой айди!
# BOT_USERNAME = "@Parsingwordpress_bot"
# # Путь к файлу с данными о каналах
# FILE_JSON = 'file.json'

# #yoi=20662346
# #yoi=8981176be8754bcd6dbfdb4d9f499b57

# # Путь к файлу с категориями
# CATEGORIES_JSON = 'categories.json'

# # Максимальное количество сообщений в папке data
# MAX_MESSAGES = 100000

# WEB_SERVER_HOST = "108.181.154.114"
# WEB_SERVER_PORT = 5432
# SECRET_KEY = '/QoXhzTJkyhzSKccxR+XV0pf4T2zqLfXzPlSwegi6Cs='  # Секретный ключ для Flask. Сгенерируйте случайную строку!
# ADMIN_USERNAME = 'Daniel11'  # Логин админа для входа на сайт
# ADMIN_PASSWORD = '8044$Daniel'  # Пароль админа для входа на сайт


# # Папки
# BASE_DIR = os.path.dirname(__file__) # Добавили
# DATA_FOLDER = os.path.join(BASE_DIR, 'data') # Добавили
# MESSAGES_FOLDER = os.path.join(DATA_FOLDER, 'messages') # Добавили
import os

# Bot's Django server configuration
WEB_SERVER_HOST = os.getenv('BOT_SERVER_HOST', 'parsinggrouptg-production.up.railway.app')  # Default to localhost
WEB_SERVER_PORT = os.getenv('BOT_SERVER_PORT', '8080')  # Default to 8081

# Main application URL
MAIN_APP_URL = os.getenv('PUBLIC_URL', 'https://parsinggrouptg-production.up.railway.app')

# Telegram bot configuration
BOT_TOKEN = os.getenv('BOT_TOKEN', '7923260865:AAGWm7t0Zz2PqFPI5PldEVwrOC4HZ_5oP0c')
API_ID = os.getenv('API_ID', '19840544')
API_HASH = os.getenv('API_HASH', 'c839f28bad345082329ec086fca021fa')

# Maintain backwards compatibility with old names
TOKEN_BOT = BOT_TOKEN  # For backwards compatibility
ADMIN_ID = 7265248372  # Admin ID in number format
BOT_USERNAME = "@Channels_hunt_bot"

# File paths
FILE_JSON = 'file.json'
CATEGORIES_JSON = 'categories.json'

# Message limits
MAX_MESSAGES = 100000

# Directory configuration
BASE_DIR = os.path.dirname(__file__)
DATA_FOLDER = os.path.join(BASE_DIR, 'data')
MESSAGES_FOLDER = os.path.join(DATA_FOLDER, 'messages')

# Create necessary directories
os.makedirs(DATA_FOLDER, exist_ok=True)
os.makedirs(MESSAGES_FOLDER, exist_ok=True)

# Admin configuration
ADMIN_USERNAME = os.getenv('ADMIN_USERNAME', 'DAndy')
ADMIN_PASSWORD = os.getenv('ADMIN_PASSWORD', 'Remoreid19976')
SECRET_KEY = os.getenv('SECRET_KEY', '/QoXhzTJkyhzSKccxR+XV0pf4T2zqLfXzPlSwegi6Cs=')

#yoi=20662346
#yoi=8981176be8754bcd6dbfdb4d9f499b57

# Виправлено формат WEB_SERVER_HOST
WEB_SERVER_HOST2 = "108.181.154.114"
