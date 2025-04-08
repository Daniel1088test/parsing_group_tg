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

# Встановлюємо параметри підключення до бази даних, якщо не встановлені
if [ -z "$DATABASE_URL" ]; then
    export DATABASE_URL="postgresql://postgres:urCNhXdwvbqOvvEsJDffIiDUMcLhAvcs@postgres.railway.internal:5432/railway"
    echo "Setting DATABASE_URL directly from script"
fi

# Встановлюємо окремі змінні PostgreSQL для додаткової надійності
export PGHOST="postgres.railway.internal"
export PGPORT="5432"
export PGDATABASE="railway"
export PGUSER="postgres"
export PGPASSWORD="urCNhXdwvbqOvvEsJDffIiDUMcLhAvcs"

echo "Using PORT: $PORT"
echo "PUBLIC_URL: $PUBLIC_URL"

# Create necessary directories
mkdir -p staticfiles media data/messages data/sessions

# Друкуємо інформацію про змінні бази даних
echo "Database environment variables:"
echo "DATABASE_URL: postgresql://postgres:****@postgres.railway.internal:5432/railway"
echo "PGHOST: ${PGHOST}"
echo "PGDATABASE: ${PGDATABASE}"
echo "PGUSER: ${PGUSER}"
echo "PGPORT: ${PGPORT}"

# Перевіряємо підключення до бази даних
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
        print('Database connection successful!')
        return True
    except Exception as e:
        print(f'Database connection failed: {e}')
        return False

# Спроба підключитися до бази даних з повторами
retries = 5
for i in range(retries):
    if check_db_connection():
        sys.exit(0)
    else:
        print(f'Retry {i+1}/{retries} in 3 seconds...')
        time.sleep(3)

print('Failed to connect to database after multiple attempts')
sys.exit(1)
" || { echo "Database connection failed, but continuing..."; sleep 5; }

# Prepare the environment
echo "Preparing environment..."
python manage.py collectstatic --noinput

# Застосовуємо міграції з виведенням детальної інформації
echo "Running migrations..."
python manage.py migrate --noinput --verbosity 2 || { 
    echo "Migrations failed! Checking database structure..."; 
    python manage.py inspectdb admin_panel_category;
    echo "Trying to run migrations again with more aggressive approach...";
    python manage.py migrate --noinput --run-syncdb;
    sleep 5;
}

# Kill any existing Gunicorn processes
pkill -f gunicorn || echo "No gunicorn processes running."

# Очищаємо сесійні файли Telethon для уникнення конфліктів
echo "Clearing Telethon session files..."
find . -type f -name "*.session*" -delete 2>/dev/null || echo "No session files found"

# Start the web server
echo "Starting web server..."
gunicorn core.wsgi:application --bind 0.0.0.0:$PORT --workers=1 --threads=4 --worker-tmp-dir /dev/shm --log-level info --timeout 120 &
GUNICORN_PID=$!
echo "Gunicorn started with PID: $GUNICORN_PID"

# Give Gunicorn time to fully start
echo "Waiting for web server to initialize..."
sleep 10

# Start the bot
echo "Starting bot process..."
python run.py &
BOT_PID=$!
echo "Bot started with PID: $BOT_PID"

# Monitor processes
echo "All processes started. Monitoring..."
wait $GUNICORN_PID 