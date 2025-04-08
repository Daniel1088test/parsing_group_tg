#!/bin/bash
set -e

echo "===================== Starting Railway Deployment ====================="

# Create required directories first
echo "Creating required directories..."
mkdir -p media/messages
mkdir -p staticfiles/img
mkdir -p data/sessions

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
" || echo "Warning: Could not create placeholder images"

# Run session fixes - with additional error handling
echo "Fixing sessions and media..."
python manage.py fix_sessions || echo "Warning: fix_sessions command had errors but continuing deployment"

# Start the server
echo "Starting Django server..."
python manage.py runserver 0.0.0.0:8080 