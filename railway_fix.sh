#!/bin/bash
# Script to fix migration issues on Railway

echo "=== Starting migration fix ==="

# Fake the problematic migrations
echo "Faking problematic migrations..."
python manage.py migrate admin_panel 0002_auto_20250409_0000 --fake
python manage.py migrate admin_panel 0003_merge_final --fake
python manage.py migrate admin_panel 0004_fake_migration --fake

# Run the full migration
echo "Running full migration..."
python manage.py migrate

# Create health check files
echo "Creating health check files..."
echo "OK" > health.txt
echo "OK" > health.html
echo "OK" > healthz.txt
echo "OK" > healthz.html

echo "=== Migration fix completed ===" 