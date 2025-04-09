import os

# Get variables from environment with fallbacks
API_HASH = os.environ.get('API_HASH', "c839f28bad345082329ec086fca021fa")
API_ID = os.environ.get('API_ID', "19840544") 
TOKEN_BOT = os.environ.get('BOT_TOKEN', "8102516142:AAFTsVXXujHHKoX2KZGqZXBHPBznfgh7kg0")
ADMIN_ID = int(os.environ.get('ADMIN_ID', "574349489"))
BOT_USERNAME = os.environ.get('BOT_USERNAME', "chan_parsing_mon_bot")

# File paths
FILE_JSON = 'file.json'  # Channel data file
CATEGORIES_JSON = 'categories.json'  # Categories file

# Message limits
MAX_MESSAGES = 100000

# Server configuration
WEB_SERVER_HOST = os.environ.get('WEB_SERVER_HOST', "127.0.0.1")  # Internal server host
WEB_SERVER_PORT = os.environ.get('WEB_SERVER_PORT', "8080")  # Internal server port
WEB_SERVER_HOST2 = os.environ.get('WEB_SERVER_HOST2', "108.181.154.114")

# Railway environment variables
RAILWAY_PUBLIC_DOMAIN = os.environ.get('RAILWAY_PUBLIC_DOMAIN', 'parsinggrouptg-production.up.railway.app')
RAILWAY_TCP_PROXY_DOMAIN = os.environ.get('RAILWAY_TCP_PROXY_DOMAIN', 'postgres.railway.internal')
RAILWAY_TCP_PROXY_PORT = os.environ.get('RAILWAY_TCP_PROXY_PORT', '5432')

# Public URL for the bot
# Default to RAILWAY_PUBLIC_DOMAIN if available, otherwise hardcoded URL
if os.environ.get('PUBLIC_URL'):
    PUBLIC_URL = os.environ.get('PUBLIC_URL')
elif os.environ.get('RAILWAY_STATIC_URL'):
    PUBLIC_URL = f"https://{os.environ.get('RAILWAY_STATIC_URL')}"
elif os.environ.get('RAILWAY_PUBLIC_DOMAIN'):
    PUBLIC_URL = f"https://{os.environ.get('RAILWAY_PUBLIC_DOMAIN')}"
else:
    PUBLIC_URL = "https://parsinggrouptg-production.up.railway.app"

# Always ensure URL starts with https://
if not PUBLIC_URL.startswith('http'):
    PUBLIC_URL = f"https://{PUBLIC_URL}"

print(f"Bot will use PUBLIC_URL: {PUBLIC_URL}")

# Database configuration from Railway
DATABASE_URL = os.environ.get('DATABASE_URL', '')
PGHOST = os.environ.get('PGHOST', 'postgres.railway.internal')
PGPORT = os.environ.get('PGPORT', '5432')
PGDATABASE = os.environ.get('PGDATABASE', 'railway')
PGUSER = os.environ.get('PGUSER', 'postgres')
PGPASSWORD = os.environ.get('PGPASSWORD', '')

# Security configuration
SECRET_KEY = os.environ.get('SECRET_KEY', '/QoXhzTJkyhzSKccxR+XV0pf4T2zqLfXzPlSwegi6Cs=')
ADMIN_USERNAME = os.environ.get('ADMIN_USERNAME', 'DAndy')
ADMIN_PASSWORD = os.environ.get('ADMIN_PASSWORD', 'Remoreid19976')

# Directory structure - use absolute paths
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_FOLDER = os.path.join(BASE_DIR, 'data')
MESSAGES_FOLDER = os.path.join(DATA_FOLDER, 'messages')
SESSIONS_DIR = os.path.join(DATA_FOLDER, 'sessions')

# Create necessary directories
for directory in [DATA_FOLDER, MESSAGES_FOLDER, SESSIONS_DIR]:
    os.makedirs(directory, exist_ok=True)
