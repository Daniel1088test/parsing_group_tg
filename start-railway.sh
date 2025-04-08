#!/bin/bash
set -e

echo "===================== Starting Railway Deployment ====================="

# Set PYTHONPATH для доступу до пакетів з поточної директорії
export PYTHONPATH=$PYTHONPATH:$(pwd)

# Створення необхідних директорій
echo "Creating required directories..."
mkdir -p media/messages
mkdir -p staticfiles/img
mkdir -p data/sessions
mkdir -p static/img

# Встановлення правильних прав доступу
echo "Setting directory permissions..."
chmod -R 755 media
chmod -R 755 staticfiles
chmod -R 755 data
chmod -R 755 static

# Очищення файлів кешу Python
echo "Cleaning Python cache files..."
find . -name "*.pyc" -delete
find . -name "__pycache__" -type d -exec rm -rf {} +

# Створення файлу health check для Railway
echo "Creating health check files..."
echo "/health" > healthcheck.txt
echo "200 OK" >> healthcheck.txt

# Створення статичних health файлів для всіх можливих запитів
echo "Creating static health check files..."
for DIR in "." "static" "staticfiles"; do
  for FILE in "health.html" "healthz.html" "health.txt" "healthz.txt"; do
    echo "OK" > $DIR/$FILE
    chmod 644 $DIR/$FILE
  done
done

# Створення placeholder файлів для медіа
echo "Creating placeholder images..."
python -c '
from PIL import Image, ImageDraw
import os

# Ensure directories exist
os.makedirs("staticfiles/img", exist_ok=True)
os.makedirs("static/img", exist_ok=True)

# Create placeholders
for path, text in [
    ("staticfiles/img/placeholder-image.png", "IMAGE"),
    ("staticfiles/img/placeholder-video.png", "VIDEO"),
    ("static/img/placeholder-image.png", "IMAGE"),
    ("static/img/placeholder-video.png", "VIDEO"),
]:
    try:
        img = Image.new("RGB", (300, 200), color=(240, 240, 240))
        draw = ImageDraw.Draw(img)
        draw.rectangle([(0, 0), (299, 199)], outline=(200, 200, 200), width=2)
        draw.text((150, 100), text, fill=(100, 100, 100))
        img.save(path)
        print(f"Created {path}")
    except Exception as e:
        print(f"Error creating {path}: {e}")
'

# Виправлення проблем з базою даних - напряму
echo "Running direct database fix..."
python scripts/direct_db_fix.py || echo "Direct database fix failed but continuing"

# Запуск міграцій
echo "Running migrations..."
python manage.py migrate || echo "Migration failed, will try with --fake-initial"
python manage.py migrate --fake-initial || echo "Migration with --fake-initial failed, trying individually"

# Якщо міграція не вдалася, пробуємо послідовно для кожного додатку
if [ $? -ne 0 ]; then
  echo "Applying migrations app by app..."
  for APP in admin auth contenttypes sessions admin_panel; do
    python manage.py migrate $APP --fake-initial || echo "Migration for $APP failed but continuing"
  done
fi

# Збір статичних файлів
echo "Collecting static files..."
python manage.py collectstatic --noinput || echo "Collectstatic failed but continuing"

# Запуск Telegram парсера у фоні
echo "Starting Telegram parser in background..."
python run_parser.py &
PARSER_PID=$!
echo "Parser started with PID: $PARSER_PID"

# Виведення інформації про середовище
echo "Environment information:"
echo "RAILWAY_ENVIRONMENT: $RAILWAY_ENVIRONMENT"
echo "RAILWAY_PUBLIC_DOMAIN: $RAILWAY_PUBLIC_DOMAIN"
echo "DATABASE_URL is ${DATABASE_URL:+set}"

# Запуск Django сервера
echo "Starting Django server..."
exec python manage.py runserver 0.0.0.0:8080 