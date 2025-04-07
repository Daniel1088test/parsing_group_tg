#!/bin/bash

# Make script exit on any error
set -e

# Set the PORT from the environment variable or use default 8000
export PORT=${PORT:-8000}
echo "Using PORT: $PORT"

# Database settings - use these if DATABASE_URL is not set
if [ -z "$DATABASE_URL" ]; then
    echo "WARNING: DATABASE_URL not found, setting it manually..."
    echo "This should not happen in production. Make sure to set DATABASE_URL in Railway dashboard!"
    export DATABASE_URL="postgresql://postgres:urCNhXdwvbqOvvEsJDffIiDUMcLhAvcs@switchback.proxy.rlwy.net:10052/railway"
fi

# Set up web server host and port for Django
export WEB_SERVER_HOST="0.0.0.0"  # Listen on all interfaces
export WEB_SERVER_PORT="$PORT"
export DJANGO_SETTINGS_MODULE=core.settings

# Run migrations first
echo "Running database migrations..."
bash migrate.sh

# Ensure directories exist
mkdir -p staticfiles
mkdir -p media

# Collect static files
echo "Collecting static files..."
python manage.py collectstatic --noinput

# Start the application in production mode
if [ "$RAILWAY_ENVIRONMENT" = "production" ]; then
    echo "Starting application in production mode on $WEB_SERVER_HOST:$PORT..."
    # Start Gunicorn for production
    gunicorn core.wsgi:application --bind $WEB_SERVER_HOST:$PORT --workers 2 --threads 2 &
    # Start the bot separately
    python run.py
else
    # For development, just use the run.py script which starts everything
    echo "Starting application in development mode on $WEB_SERVER_HOST:$PORT..."
    python run.py 