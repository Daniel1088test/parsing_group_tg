#!/bin/bash

echo "=== Railway Startup ==="
echo "Making sure essential packages are installed..."
pip install dj-database-url python-dotenv whitenoise django-storages psycopg2-binary

echo "Running fix requirements script..."
python fix_requirements.py

echo "Running Django settings fix script..."
python fix_django_settings.py

echo "Setting up environment variables..."
if [ -f .env ]; then
    echo "Loading environment from .env file"
    export $(cat .env | grep -v '^#' | xargs)
fi

# Set Railway environment flag
export RAILWAY_ENVIRONMENT=production

# Set Django settings
export DJANGO_SETTINGS_MODULE=core.settings

# Setup health check files
echo "Creating health check files..."
for file in health.txt healthz.txt health.html healthz.html; do
    echo "OK" > $file
    echo "OK" > static/$file
    echo "OK" > staticfiles/$file
done

echo "Starting application via run.py..."
python run.py 