#!/bin/bash

# Set the PORT from the environment variable or use default 8000
export PORT=${PORT:-8000}
echo "Using PORT: $PORT"

# Database settings - use these if DATABASE_URL is not set
if [ -z "$DATABASE_URL" ]; then
    echo "DATABASE_URL not found, setting it manually..."
    export DATABASE_URL="postgresql://postgres:urCNhXdwvbqOvvEsJDffIiDUMcLhAvcs@switchback.proxy.rlwy.net:10052/railway"
fi

# Set up web server host and port for Django
export WEB_SERVER_HOST="0.0.0.0"  # Listen on all interfaces
export WEB_SERVER_PORT="$PORT"

# Run migrations first
bash migrate.sh

# Collect static files
echo "Collecting static files..."
python manage.py collectstatic --noinput

# Start the application
echo "Starting application on $WEB_SERVER_HOST:$PORT..."
python run.py 