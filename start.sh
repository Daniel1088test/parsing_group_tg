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

# Create necessary directories
mkdir -p staticfiles
mkdir -p media

# Run migrations first (with error handling)
echo "Running database migrations..."
set +e  # Temporarily disable exit on error
python manage.py migrate
MIGRATE_EXIT_CODE=$?
set -e  # Re-enable exit on error

if [ $MIGRATE_EXIT_CODE -ne 0 ]; then
    echo "Warning: Migration failed with exit code $MIGRATE_EXIT_CODE but continuing startup..."
fi

# Collect static files
echo "Collecting static files..."
python manage.py collectstatic --noinput

# Set Railway environment to production if not already set
export RAILWAY_ENVIRONMENT=${RAILWAY_ENVIRONMENT:-production}

echo "Starting application in $RAILWAY_ENVIRONMENT mode on $WEB_SERVER_HOST:$PORT..."

# For Railway deployment, we need to use gunicorn as the main process
if [ "$RAILWAY_ENVIRONMENT" = "production" ]; then
    echo "Starting Django with gunicorn on $WEB_SERVER_HOST:$PORT..."
    
    # Start the Telegram bot in the background
    echo "Starting Telegram bot in background..."
    python run.py &
    
    # Start gunicorn as the main process (not in background)
    echo "Starting gunicorn as main process..."
    exec gunicorn core.wsgi:application --bind $WEB_SERVER_HOST:$PORT --workers 2 --threads 2 --timeout 120 --access-logfile - --error-logfile -
else
    # For development, just use the run.py script which starts everything
    python run.py 