#!/bin/bash
set -e

echo "===================== Starting Railway Deployment ====================="

echo "Running emergency fix for media directories..."
python fix_media_directories.py || echo "Warning: Media directory fix failed but continuing"

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

# Use our proper Django-configured session fix script
if [ -f "scripts/fix_sessions.py" ]; then
    echo "Running session fixes with properly configured script..."
    python scripts/fix_sessions.py || echo "Warning: Session fix script had errors but continuing deployment"
else
    # Fall back to the old method if the script doesn't exist
    echo "Fixing sessions using legacy method..."
    python manage.py fix_sessions || echo "Warning: fix_sessions command had errors but continuing deployment"
fi

# Create required symlinks for consistent media access
if [ -f "scripts/create_symlinks.py" ]; then
    echo "Creating symbolic links with properly configured script..."
    python scripts/create_symlinks.py || echo "Warning: Symlink creation script had errors but continuing deployment"
else
    echo "Creating symbolic links using legacy method..."
    # Create symlink in static directory to media
    if [ ! -L "staticfiles/media" ]; then
        ln -sf "$(pwd)/media" "staticfiles/media" || echo "Warning: Could not create symlink for media"
    fi
    
    # Ensure /app/media/messages is linked to the media directory
    if [ ! -L "/app/media/messages" ]; then
        mkdir -p /app/media
        ln -sf "$(pwd)/media/messages" "/app/media/messages" || echo "Warning: Could not create symlink for media"
    fi
fi

# Make the scripts directly executable for use in Railway
if [ -f "scripts/fix_sessions.py" ]; then
    chmod +x scripts/fix_sessions.py
fi
if [ -f "scripts/create_symlinks.py" ]; then
    chmod +x scripts/create_symlinks.py
fi

# Print environment information
echo "Environment information:"
echo "RAILWAY_ENVIRONMENT: $RAILWAY_ENVIRONMENT"
echo "RAILWAY_PUBLIC_DOMAIN: $RAILWAY_PUBLIC_DOMAIN"

# Start the parser in background
echo "Starting Telegram parser in background..."
python run_parser.py &
PARSER_PID=$!
echo "Parser started with PID: $PARSER_PID"

# Start the server
echo "Starting Django server..."
exec python manage.py runserver 0.0.0.0:8080