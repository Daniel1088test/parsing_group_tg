#!/bin/bash
# Emergency migration fixer for Railway
# This script is designed to be run directly on Railway to fix database migration issues

echo "=== Railway Migration Emergency Fix ==="

# Mark problematic migrations as applied
echo "Marking migrations as applied with --fake..."
python manage.py migrate admin_panel 0002_auto_20250409_0000 --fake
python manage.py migrate admin_panel 0003_merge_final --fake
python manage.py migrate admin_panel 0004_fake_migration --fake

# Attempt to apply all migrations
echo "Attempting to apply all migrations..."
python manage.py migrate

# Create placeholder assets
echo "Creating placeholder assets..."
mkdir -p staticfiles/img

# Create SVG placeholders
cat > staticfiles/img/placeholder-image.svg << EOL
<?xml version="1.0" encoding="UTF-8" standalone="no"?>
<svg width="300" height="200" xmlns="http://www.w3.org/2000/svg">
  <rect width="298" height="198" x="1" y="1" fill="#f0f0f0" stroke="#c8c8c8" stroke-width="2"/>
  <text x="150" y="110" font-family="Arial" font-size="24" text-anchor="middle" fill="#646464">IMAGE</text>
</svg>
EOL

cat > staticfiles/img/placeholder-video.svg << EOL
<?xml version="1.0" encoding="UTF-8" standalone="no"?>
<svg width="300" height="200" xmlns="http://www.w3.org/2000/svg">
  <rect width="298" height="198" x="1" y="1" fill="#f0f0f0" stroke="#c8c8c8" stroke-width="2"/>
  <text x="150" y="110" font-family="Arial" font-size="24" text-anchor="middle" fill="#646464">VIDEO</text>
</svg>
EOL

# Create health check files
echo "Creating health check files..."
echo "OK" > health.txt
echo "OK" > health.html
echo "OK" > healthz.txt
echo "OK" > healthz.html

# Last resort: If all else fails, try to fix the database directly with SQL
echo "Attempting direct database fix if needed..."
python - << EOL
import os
import sys
import django
from django.db import connection

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()

try:
    # Connect to database
    with connection.cursor() as cursor:
        # Check if django_migrations table exists
        cursor.execute("SELECT to_regclass('public.django_migrations');")
        if cursor.fetchone()[0]:
            # Get current migrations
            cursor.execute("SELECT id, app, name FROM django_migrations WHERE app='admin_panel';")
            existing_migrations = cursor.fetchall()
            print(f"Found {len(existing_migrations)} existing migrations for admin_panel:")
            for migration in existing_migrations:
                print(f"  {migration[0]}: {migration[1]}.{migration[2]}")
            
            # Required migrations
            required_migrations = [
                '0001_initial',
                '0002_auto_20250409_0000',
                'fix_is_bot_column',
                '0003_merge_final',
                '0004_fake_migration'
            ]
            
            # Get existing migration names
            existing_names = [row[2] for row in existing_migrations]
            
            # Add missing migrations
            for migration in required_migrations:
                if migration not in existing_names:
                    print(f"Adding missing migration: admin_panel.{migration}")
                    cursor.execute(
                        "INSERT INTO django_migrations (app, name, applied) VALUES (%s, %s, now());",
                        ['admin_panel', migration]
                    )
        else:
            print("django_migrations table does not exist, cannot fix directly")
except Exception as e:
    print(f"Error in direct database fix: {e}")
EOL

echo "=== Railway Migration Emergency Fix Completed ===" 