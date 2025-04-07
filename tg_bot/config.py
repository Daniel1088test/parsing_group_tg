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
WEB_SERVER_HOST = os.getenv('BOT_SERVER_HOST', '127.0.0.1')  # Default to localhost
WEB_SERVER_PORT = os.getenv('BOT_SERVER_PORT', '8081')  # Default to 8081

# Main application URL
MAIN_APP_URL = os.getenv('PUBLIC_URL', 'https://parsinggrouptg-production.up.railway.app')

# Telegram bot configuration
BOT_TOKEN = os.getenv('BOT_TOKEN')
API_ID = os.getenv('API_ID')
API_HASH = os.getenv('API_HASH')

#yoi=20662346
#yoi=8981176be8754bcd6dbfdb4d9f499b57

# Путь к файлу с категориями
CATEGORIES_JSON = 'categories.json'

# Максимальное количество сообщений в папке data
MAX_MESSAGES = 100000
# Виправлено формат WEB_SERVER_HOST
WEB_SERVER_HOST2 = "108.181.154.114"
SECRET_KEY = '/QoXhzTJkyhzSKccxR+XV0pf4T2zqLfXzPlSwegi6Cs='  # Секретный ключ для Flask. Сгенерируйте случайную строку!
ADMIN_USERNAME = 'DAndy'  # Логин админа для входа на сайт
ADMIN_PASSWORD = 'Remoreid19976'  # Пароль админа для входа на сайт


# Папки
BASE_DIR = os.path.dirname(__file__) # Добавили
DATA_FOLDER = os.path.join(BASE_DIR, 'data') # Добавили
MESSAGES_FOLDER = os.path.join(DATA_FOLDER, 'messages') # Добавили
