#!/bin/bash
# Comprehensive startup script for Django+Telegram Parser on Railway.app
set -e

# Log startup process
echo "======== STARTING DEPLOYMENT $(date) ========"
echo "Environment: RAILWAY_ENVIRONMENT=${RAILWAY_ENVIRONMENT:-local}"
echo "Working directory: $(pwd)"

# Running emergency fix for media directories
echo "Running emergency fix for media directories..."
python fix_media_directories.py || echo "Warning: Media directory fix failed but continuing"

# Create essential directories with clear logging
echo "Creating essential directories..."
mkdir -p staticfiles/media/messages
mkdir -p staticfiles/health
mkdir -p media/messages
mkdir -p logs
mkdir -p media/messages
mkdir -p staticfiles/img
mkdir -p data/sessions

# Set directory permissions
echo "Setting directory permissions..."
chmod -R 755 media
chmod -R 755 staticfiles
chmod -R 755 data

# Ensure all scripts are executable
find ./scripts -name "*.py" -exec chmod +x {} \;
find . -name "*.sh" -exec chmod +x {} \;

# Setup health check files (critical for Railway)
echo "Setting up health check files..."
echo "OK" > staticfiles/health/index.html
echo "OK" > staticfiles/health.html
echo "OK" > staticfiles/healthz.html
echo "OK" > health.html

# Install core dependencies
if [ -n "$RAILWAY_ENVIRONMENT" ]; then
    echo "Installing essential dependencies..."
    pip install --no-cache-dir psycopg2-binary pillow django-cors-headers python-dotenv
fi

# Fix Python path to avoid import errors
export PYTHONPATH=$PYTHONPATH:$(pwd)

# Database connection and schema fix
echo "=== DATABASE SETUP PHASE ==="
echo "Checking database connection and fixing schema..."

# Run direct database fix script with retries
MAX_RETRIES=5
RETRY_DELAY=2
RETRY_COUNT=0

while [ $RETRY_COUNT -lt $MAX_RETRIES ]; do
    echo "Running database fix (attempt $((RETRY_COUNT+1))/$MAX_RETRIES)..."
    
    if python direct_db_fix.py; then
        echo "✓ Database fix successful"
        break
    else
        echo "✗ Database fix failed, retrying in $RETRY_DELAY seconds..."
        RETRY_COUNT=$((RETRY_COUNT+1))
        sleep $RETRY_DELAY
        RETRY_DELAY=$((RETRY_DELAY*2))  # Exponential backoff
    fi
done

# Migrate with Django migrations - phase 1: makemigrations
echo "=== DJANGO MIGRATIONS PHASE ==="
echo "Creating migrations for model changes..."
python manage.py makemigrations admin_panel --noinput || true
echo "Creating any other needed migrations..."
python manage.py makemigrations --noinput || true

# Migrate with Django migrations - phase 2: apply migrations
echo "Applying migrations..."
RETRY_COUNT=0
RETRY_DELAY=2

while [ $RETRY_COUNT -lt $MAX_RETRIES ]; do
    echo "Migration attempt $((RETRY_COUNT+1))/$MAX_RETRIES"
    
    if python manage.py migrate --noinput; then
        echo "✓ Migrations successfully applied"
        break
    else
        echo "✗ Migration failed, retrying with alternative approach..."
        if [ $RETRY_COUNT -eq 0 ]; then
            # Try without TelegramSession model on first retry
            python manage.py migrate auth admin contenttypes sessions --noinput
        elif [ $RETRY_COUNT -eq 1 ]; then
            # Try with fake initial on second retry
            python manage.py migrate --fake-initial --noinput
        fi
        
        RETRY_COUNT=$((RETRY_COUNT+1))
        sleep $RETRY_DELAY
        RETRY_DELAY=$((RETRY_DELAY*2))
    fi
done

# Collect static files
echo "=== STATIC FILES PHASE ==="
echo "Collecting static files..."
python manage.py collectstatic --noinput --clear

# Creating placeholder images for missing media
echo "=== MEDIA SETUP PHASE ==="
echo "Creating placeholder images..."
python -c '
import os
from PIL import Image, ImageDraw, ImageFont
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
        draw.text(text_position, text, fill=(100, 100, 100), anchor="mm")
        
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

# Start the background services
echo "=== STARTING SERVICES ==="

# Try fix script-specific imports first
echo "Running railway startup script fixes..."
python scripts/railway_startup_fix.py || true

# Start Telethon parser in the background with output to a log file
echo "Starting Telegram parser in background..."
nohup python run_parser.py > ./logs/parser.log 2>&1 &
PARSER_PID=$!
echo "✓ Started Telegram parser (PID: $PARSER_PID)"

# Final check before starting web server
echo "=== FINAL CHECKS ==="
python manage.py check --deploy || true

# Start the Django web server
echo "=== STARTING WEB SERVER ==="
echo "Starting Django on 0.0.0.0:8080..."
exec python manage.py runserver 0.0.0.0:8080