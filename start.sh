#!/bin/bash

# Exit on any error
set -e

echo "Starting deployment script at $(date)"

# Встановлюємо необхідні пакети для роботи з PostgreSQL
echo "Installing required packages..."
pip install dj-database-url psycopg2-binary

# Set required environment variables
export PORT=${PORT:-8080}
export RAILWAY_PUBLIC_DOMAIN="${RAILWAY_PUBLIC_DOMAIN:-parsinggrouptg-production.up.railway.app}"
export PUBLIC_URL="https://$RAILWAY_PUBLIC_DOMAIN"

echo "Using PORT: $PORT"
echo "PUBLIC_URL: $PUBLIC_URL"

# Create necessary directories
mkdir -p staticfiles media data/messages data/sessions

# Друкуємо інформацію про змінні бази даних
echo "Database environment variables:"
echo "DATABASE_URL: ${DATABASE_URL:-Not set}"
echo "PGHOST: ${PGHOST:-Not set}"
echo "PGDATABASE: ${PGDATABASE:-Not set}"
echo "PGUSER: ${PGUSER:-Not set}"
echo "PGPORT: ${PGPORT:-Not set}"

# Якщо DATABASE_URL не встановлено, але є окремі змінні PostgreSQL
if [ -z "$DATABASE_URL" ] && [ ! -z "$PGHOST" ] && [ ! -z "$PGDATABASE" ] && [ ! -z "$PGUSER" ] && [ ! -z "$PGPASSWORD" ]; then
    export DATABASE_URL="postgresql://${PGUSER}:${PGPASSWORD}@${PGHOST}:${PGPORT:-5432}/${PGDATABASE}"
    echo "Created DATABASE_URL from individual PostgreSQL variables"
fi

# Перевіряємо підключення до бази даних
if [ ! -z "$DATABASE_URL" ]; then
    echo "Testing database connection..."
    python -c "
import sys
import psycopg2
import time
import os

# Функція для перевірки підключення до бази даних
def check_db_connection():
    try:
        db_url = os.environ.get('DATABASE_URL')
        conn = psycopg2.connect(db_url)
        cursor = conn.cursor()
        cursor.execute('SELECT 1')
        cursor.close()
        conn.close()
        return True
    except Exception as e:
        print(f'Database connection failed: {e}')
        return False

# Спроба підключитися до бази даних з повторами
retries = 5
for i in range(retries):
    if check_db_connection():
        print('Database connection successful!')
        sys.exit(0)
    else:
        print(f'Retry {i+1}/{retries} in 3 seconds...')
        time.sleep(3)

print('Failed to connect to database after multiple attempts')
sys.exit(1)
" || echo "Database connection failed, but continuing..."
fi

# Prepare the environment
echo "Preparing environment..."
python manage.py collectstatic --noinput
python manage.py migrate --noinput

# Kill any existing Gunicorn processes
pkill -f gunicorn || echo "No gunicorn processes running."

# Очищаємо сесійні файли Telethon для уникнення конфліктів
echo "Clearing Telethon session files..."
find . -type f -name "*.session*" -delete 2>/dev/null || echo "No session files found"

# Start the web server
echo "Starting web server..."
gunicorn core.wsgi:application --bind 0.0.0.0:$PORT --workers=1 --threads=4 --worker-tmp-dir /dev/shm --log-level info &
GUNICORN_PID=$!
echo "Gunicorn started with PID: $GUNICORN_PID"

# Give Gunicorn time to fully start
echo "Waiting for web server to initialize..."
sleep 5

# Create a simplified bot runner script
cat > run_bot_only.py << 'EOF'
import os
import asyncio
import logging
import django
from datetime import datetime

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger('telegram_bot')

# Setup Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()

async def main():
    """Run the Telegram bot"""
    try:
        from tg_bot.bot import main as bot_main
        await bot_main()
    except Exception as e:
        logger.error(f"Error running bot: {e}")
        import traceback
        logger.error(traceback.format_exc())

if __name__ == "__main__":
    logger.info("Starting Telegram bot runner")
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Bot stopped by user")
    except Exception as e:
        logger.error(f"Fatal error: {e}")
        import traceback
        logger.error(traceback.format_exc())
EOF

# Start the bot
echo "Starting bot process..."
python run_bot_only.py &
BOT_PID=$!
echo "Bot started with PID: $BOT_PID"

# Monitor processes
echo "All processes started. Monitoring..."
wait $GUNICORN_PID 