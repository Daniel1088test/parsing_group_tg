#!/bin/bash
set -e

echo "===================== Starting Railway Deployment ====================="

# Create required directories with proper permissions
echo "Creating required directories..."
mkdir -p media/messages
mkdir -p staticfiles/img
mkdir -p data/sessions

# Set directory permissions
echo "Setting directory permissions..."
chmod -R 755 media
chmod -R 755 staticfiles
chmod -R 755 data

# Run migrations - continue on error
echo "Running migrations..."
python manage.py migrate || echo "Warning: Migration had errors but continuing deployment"

# Collect static files
echo "Collecting static files..."
python manage.py collectstatic --noinput || echo "Warning: collectstatic had errors but continuing deployment"

# Make placeholder files if they don't exist yet
echo "Ensuring placeholder files exist..."
python -c "
from PIL import Image, ImageDraw
import os

# Create placeholders
placeholder_paths = [
    ('staticfiles/img/placeholder-image.png', 'IMAGE'),
    ('staticfiles/img/placeholder-video.png', 'VIDEO')
]

for path, text in placeholder_paths:
    if not os.path.exists(path):
        print(f'Creating {path}')
        img = Image.new('RGB', (300, 200), color=(240, 240, 240))
        draw = ImageDraw.Draw(img)
        draw.rectangle([(0, 0), (299, 199)], outline=(200, 200, 200), width=2)
        draw.text((150, 100), text, fill=(100, 100, 100))
        img.save(path)
        
        # Set file permissions
        try:
            os.chmod(path, 0o644)
            print(f'Set permissions for {path}')
        except Exception as e:
            print(f'Could not set permissions for {path}: {e}')
" || echo "Warning: Could not create placeholder images"

# Run comprehensive media fix script - critical for Railway
echo "Running comprehensive media fix script..."
python fix_railway_media.py || echo "Warning: Media fix script had errors but continuing deployment"

# Run session fixes - with additional error handling
echo "Fixing sessions and media..."
python manage.py fix_sessions || echo "Warning: fix_sessions command had errors but continuing deployment"

# Create required symlinks for consistent media access
echo "Creating symbolic links for media access..."
# Ensure /app/media/messages is linked to the media directory
if [ ! -L "/app/media/messages" ]; then
    mkdir -p /app/media
    ln -sf "$(pwd)/media/messages" "/app/media/messages" || echo "Warning: Could not create symlink for media"
fi

# Dump environment variables for debugging
echo "Environment information:"
echo "RAILWAY_ENVIRONMENT: $RAILWAY_ENVIRONMENT"
echo "RAILWAY_PUBLIC_DOMAIN: $RAILWAY_PUBLIC_DOMAIN"
echo "MEDIA_ROOT: $(python -c 'from django.conf import settings; print(settings.MEDIA_ROOT)')"
echo "STATIC_ROOT: $(python -c 'from django.conf import settings; print(settings.STATIC_ROOT)')"

# Start the parser in background
echo "Starting Telegram parser in background..."
python run_parser.py &
PARSER_PID=$!
echo "Parser started with PID: $PARSER_PID"

# Start the server
echo "Starting Django server..."
exec python manage.py runserver 0.0.0.0:8080 