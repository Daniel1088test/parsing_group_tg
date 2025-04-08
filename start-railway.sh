#!/bin/bash
# Comprehensive startup script for Django+Telegram Parser on Railway.app
set -e

# Log startup process
echo "======== STARTING DEPLOYMENT $(date) ========"
echo "Environment: RAILWAY_ENVIRONMENT=${RAILWAY_ENVIRONMENT:-local}"
echo "Working directory: $(pwd)"

# Ensure all scripts are executable
find ./scripts -name "*.py" -exec chmod +x {} \; 2>/dev/null || true
find . -name "*.sh" -exec chmod +x {} \; 2>/dev/null || true
find ./tg_bot -name "*.py" -exec chmod +x {} \; 2>/dev/null || true

# Create essential directories with clear logging
echo "Creating essential directories..."
mkdir -p staticfiles/media/messages
mkdir -p staticfiles/health
mkdir -p media/messages
mkdir -p logs
mkdir -p static
mkdir -p data/sessions

# Setup health check files (critical for Railway)
echo "Setting up health check files..."
echo "OK" > staticfiles/health/index.html
echo "OK" > staticfiles/health.html
echo "OK" > staticfiles/healthz.html
echo "OK" > health.html

# Install core dependencies
if [ -n "$RAILWAY_ENVIRONMENT" ]; then
    echo "Installing essential dependencies..."
    pip install --no-cache-dir psycopg2-binary pillow django-cors-headers python-dotenv whitenoise gunicorn aiogram telethon
fi

# Fix Python path to avoid import errors
export PYTHONPATH=$PYTHONPATH:$(pwd)

# Database connection and schema fix
echo "=== DATABASE SETUP PHASE ==="
echo "Checking database connection and fixing schema..."

# Run direct database fix script with retries (with timeout)
MAX_RETRIES=5
RETRY_DELAY=2
RETRY_COUNT=0

while [ $RETRY_COUNT -lt $MAX_RETRIES ]; do
    echo "Running database fix (attempt $((RETRY_COUNT+1))/$MAX_RETRIES)..."
    
    timeout 30s python direct_db_fix.py
    if [ $? -eq 0 ]; then
        echo "✓ Database fix successful"
        break
    else
        echo "✗ Database fix failed, retrying in $RETRY_DELAY seconds..."
        RETRY_COUNT=$((RETRY_COUNT+1))
        sleep $RETRY_DELAY
        RETRY_DELAY=$((RETRY_DELAY*2))  # Exponential backoff
    fi
done

# Migrate with Django migrations - phase 1: makemigrations (with timeout)
echo "=== DJANGO MIGRATIONS PHASE ==="
echo "Creating migrations for model changes..."
timeout 30s python manage.py makemigrations admin_panel --noinput || true
echo "Creating any other needed migrations..."
timeout 30s python manage.py makemigrations --noinput || true

# Migrate with Django migrations - phase 2: apply migrations (with timeout)
echo "Applying migrations..."
RETRY_COUNT=0
RETRY_DELAY=2

while [ $RETRY_COUNT -lt $MAX_RETRIES ]; do
    echo "Migration attempt $((RETRY_COUNT+1))/$MAX_RETRIES"
    
    if timeout 60s python manage.py migrate --fake-initial --noinput; then
        echo "✓ Migrations successfully applied"
        break
    else
        echo "✗ Migration failed, retrying with alternative approach..."
        if [ $RETRY_COUNT -eq 0 ]; then
            # Try without problematic migrations on first retry
            timeout 30s python manage.py migrate auth admin contenttypes sessions --noinput || true
            # Fake apply critical migrations that might cause conflicts
            for migration in admin_panel.0003_add_telegram_session_fields admin_panel.0002_auto_20250405_1810; do
                echo "Fake applying $migration"
                python manage.py migrate --fake $migration || true
            done
        elif [ $RETRY_COUNT -eq 1 ]; then
            # Second retry - force fake all migrations
            timeout 30s python manage.py migrate --fake admin_panel || true
            timeout 30s python manage.py migrate --fake-initial --noinput || true
        fi
        
        RETRY_COUNT=$((RETRY_COUNT+1))
        sleep $RETRY_DELAY
        RETRY_DELAY=$((RETRY_DELAY*2))
    fi
done

# Collect static files
echo "=== STATIC FILES PHASE ==="
echo "Collecting static files..."
timeout 30s python manage.py collectstatic --noinput --clear

# Creating placeholder images for missing media
echo "=== MEDIA SETUP PHASE ==="
echo "Creating placeholder images..."
timeout 30s python -c '
import os
from PIL import Image, ImageDraw
import sys

# Create placeholders
def create_placeholder(path, text, size=(300, 200)):
    try:
        # Ensure directory exists
        os.makedirs(os.path.dirname(path), exist_ok=True)
        
        # Create image
        img = Image.new("RGB", size, color=(240, 240, 240))
        draw = ImageDraw.Draw(img)
        
        # Draw border
        draw.rectangle([(0, 0), (size[0]-1, size[1]-1)], outline=(200, 200, 200), width=2)
        
        # Add text
        text_position = (size[0]//2, size[1]//2)
        draw.text(text_position, text, fill=(100, 100, 100))
        
        # Save
        img.save(path)
        print(f"Created {path}")
        return True
    except Exception as e:
        print(f"Error creating {path}: {e}")
        return False

# Create necessary placeholders
placeholders = [
    ("staticfiles/media/placeholder-image.png", "IMAGE"),
    ("staticfiles/media/placeholder-video.png", "VIDEO"),
    ("media/placeholder-image.png", "IMAGE"),
    ("media/placeholder-video.png", "VIDEO"),
    ("staticfiles/media/messages/placeholder-image.png", "IMAGE"),
    ("staticfiles/media/messages/placeholder-video.png", "VIDEO"),
    ("media/messages/placeholder-image.png", "IMAGE"),
    ("media/messages/placeholder-video.png", "VIDEO"),
]

success = True
for path, text in placeholders:
    if not create_placeholder(path, text):
        success = False

# Exit with status code
sys.exit(0 if success else 1)
'

# Try fix script-specific imports first
echo "Running railway startup script fixes..."
timeout 30s python scripts/railway_startup_fix.py || true

# Create superuser if needed (no wait for input - will use envvar or skip)
echo "Creating superuser if needed..."
python -c "
import os; os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings'); 
import django; django.setup();
from django.contrib.auth import get_user_model;
User = get_user_model();
username = os.environ.get('DJANGO_SUPERUSER_USERNAME', 'admin');
email = os.environ.get('DJANGO_SUPERUSER_EMAIL', 'admin@example.com');
password = os.environ.get('DJANGO_SUPERUSER_PASSWORD', 'admin');

if not User.objects.filter(username=username).exists():
    print(f'Creating superuser {username}');
    User.objects.create_superuser(username, email, password);
    print('Superuser created successfully');
else:
    print('Superuser already exists');
"

# Start the Telegram Bot and Parser using the launcher
echo "=== STARTING TELEGRAM SERVICES ==="
echo "Starting Telegram Bot and Parser using launcher..."
nohup python tg_bot/launcher.py > ./logs/launcher.log 2>&1 &
LAUNCHER_PID=$!
echo "✓ Started Telegram services (Launcher PID: $LAUNCHER_PID)"

# Final check before starting web server
echo "=== FINAL CHECKS ==="
timeout 30s python manage.py check || true

# Start the Django web server with Gunicorn for better performance
echo "=== STARTING WEB SERVER ==="
echo "Starting Django with Gunicorn on https://parsinggrouptg-production.up.railway.app/"
exec gunicorn core.wsgi:application --bind https://parsinggrouptg-production.up.railway.app/ --workers=2 --timeout=120 