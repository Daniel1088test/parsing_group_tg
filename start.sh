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
bash migrate.sh
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

# In production, use gunicorn to serve Django and run the bot in a separate process
if [ "$RAILWAY_ENVIRONMENT" = "production" ]; then
    # Start the Django application with gunicorn in the background
    # and ensure the health check endpoint is accessible
    gunicorn core.wsgi:application --bind $WEB_SERVER_HOST:$PORT --workers 2 --threads 2 --timeout 120 --access-logfile - --error-logfile - &
    GUNICORN_PID=$!
    
    # Give gunicorn time to start up
    echo "Waiting for gunicorn to start up..."
    sleep 5
    
    # Try to access the health check endpoint 
    echo "Testing health check endpoint..."
    set +e  # Don't exit on error
    curl -f http://localhost:$PORT/health/ || echo "Warning: Health check endpoint not responding but continuing startup"
    set -e  # Re-enable exit on error
    
    # Run the bot script
    echo "Starting Telegram bot..."
    python run.py
    
    # If the bot script exits, keep the container running by waiting for the gunicorn process
    wait $GUNICORN_PID
else
    # For development, just use the run.py script which starts everything
    python run.py 