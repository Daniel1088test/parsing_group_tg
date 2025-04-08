#!/bin/bash
set -e

echo "===================== Starting Railway Deployment ====================="

# Ensure scripts directory is a proper package
echo "Setting up Python packages..."
python scripts/make_package.py || echo "Package setup failed but continuing"

# Run our comprehensive startup fix script
python scripts/railway_startup_fix.py

# Clear Python cache files to ensure clean module imports
echo "Cleaning Python cache files..."
find . -name "*.pyc" -delete
find . -name "__pycache__" -type d -exec rm -rf {} +

# Run a direct merge migration to fix multiple leaf nodes issue
echo "Running direct migration fix via Django shell..."
python manage.py migrate admin_panel 0004_merge_20250408_1830 --fake || echo "Fake merge migration applied or skipped"
python manage.py migrate admin_panel 0005_fix_auth_conflict --fake || echo "Fake fields migration applied or skipped"
python manage.py migrate --fake-initial || echo "Fake-initial migration applied or skipped"

# Run our failsafe script to directly fix database columns
echo "Running failsafe database fix script..."
python scripts/failsafe_db_fix.py || echo "Failsafe database fix failed but continuing"

# Now run regular migrations
python manage.py migrate || echo "Migrations applied or skipped"

# Fix the SyntaxError by using a simpler approach
echo "Checking for run_migrations_view function..."
python -c "
import sys
try:
    import admin_panel.views
    if hasattr(admin_panel.views, 'run_migrations_view'):
        print('run_migrations_view function exists in views module')
        sys.exit(0)
    else:
        print('ERROR: run_migrations_view function NOT found in views module')
        sys.exit(1)
except Exception as e:
    print(f'Error checking views module: {e}')
    sys.exit(1)
"

# If the function doesn't exist, add it through a separate script
if [ $? -ne 0 ]; then
    echo "Adding the missing view function..."
    cat << 'EOT' > temp_add_view.py
#!/usr/bin/env python3
import os

view_function = '''
@login_required
def run_migrations_view(request):
    """View for running database migrations"""
    if request.method == 'POST':
        try:
            import os
            import subprocess
            result = subprocess.run(
                ["python", "manage.py", "migrate"],
                capture_output=True,
                text=True
            )
            if result.returncode == 0:
                messages.success(request, "Database migrations have been applied successfully.")
            else:
                messages.error(request, f"Failed to apply migrations: {result.stderr}")
        except Exception as e:
            messages.error(request, f"Error running migrations: {str(e)}")
    
    return render(request, 'admin_panel/run_migrations.html')
'''

with open('admin_panel/views.py', 'a') as f:
    f.write(view_function)
    print("Added run_migrations_view function to views.py")
EOT
    python temp_add_view.py
    rm temp_add_view.py
fi

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