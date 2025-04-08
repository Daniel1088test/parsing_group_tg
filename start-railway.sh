#!/bin/bash
set -e

echo "===================== Starting Railway Deployment ====================="

# Run migrations first
echo "Running migrations..."
python manage.py migrate

# Collect static files
echo "Collecting static files..."
python manage.py collectstatic --noinput

# Run session fixes
echo "Fixing sessions and media..."
python manage.py fix_sessions

# Start the server
echo "Starting Django server..."
python manage.py runserver 0.0.0.0:8080 