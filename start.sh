#!/bin/bash

# Exit on any error
set -e

echo "Starting deployment script at $(date)"

# Set required environment variables
export PORT=${PORT:-8080}
export RAILWAY_PUBLIC_DOMAIN="${RAILWAY_PUBLIC_DOMAIN:-parsinggrouptg-production.up.railway.app}"
export PUBLIC_URL="https://$RAILWAY_PUBLIC_DOMAIN"

echo "Using PORT: $PORT"
echo "PUBLIC_URL: $PUBLIC_URL"

# Create necessary directories
mkdir -p staticfiles media data/messages data/sessions

# Prepare the environment
echo "Preparing environment..."
python manage.py collectstatic --noinput
python manage.py migrate --noinput

# Очищаємо сесійні файли Telethon для уникнення конфліктів
echo "Clearing Telethon session files..."
find . -type f -name "*.session*" -delete 2>/dev/null || echo "No session files found"

# Start the web server
echo "Starting Gunicorn web server (PORT=$PORT)..."
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

# Monitor main web process
echo "All processes started. Monitoring..."
wait $GUNICORN_PID 