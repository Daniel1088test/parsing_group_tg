#!/bin/bash
set -e

echo "Starting deployment script for Django+Telegram Parser on Railway.app"

# Ensure script is executable on Unix systems
chmod +x ./scripts/restart_server.py ./scripts/railway_startup_fix.py ./scripts/fix_url_view.py ./scripts/fix_migrations_dependency.py

# Create essential directories
mkdir -p staticfiles
mkdir -p staticfiles/media
mkdir -p staticfiles/media/messages
mkdir -p media
mkdir -p media/messages

# Install core dependencies if running in a container environment 
if [ -n "$RAILWAY_ENVIRONMENT" ]; then
    echo "Installing psycopg2-binary for database fixes..."
    pip install psycopg2-binary
fi

# Create health check files
echo "Creating health check files..."
mkdir -p staticfiles/health
echo "OK" > staticfiles/health/index.html
echo "OK" > staticfiles/health.html

# Run core fixes before database operations
echo "Running environment and URL fixes..."
python ./scripts/railway_startup_fix.py
python ./scripts/fix_url_view.py

# Fix migrations and dependencies
echo "Fixing migrations and dependencies..."
python ./scripts/fix_migrations_dependency.py

# Database connection check and retry
echo "Checking database connection and applying fixes..."
MAX_RETRIES=5
RETRY_DELAY=2
RETRY_COUNT=0

while [ $RETRY_COUNT -lt $MAX_RETRIES ]; do
    echo "Database fix attempt $((RETRY_COUNT+1))/$MAX_RETRIES"
    
    # Run the direct database fix
    if python direct_db_fix.py; then
        echo "Database fix successful!"
        break
    else
        echo "Database fix failed, retrying in $RETRY_DELAY seconds..."
        RETRY_COUNT=$((RETRY_COUNT+1))
        sleep $RETRY_DELAY
        RETRY_DELAY=$((RETRY_DELAY*2))  # Exponential backoff
    fi
done

if [ $RETRY_COUNT -eq $MAX_RETRIES ]; then
    echo "WARNING: Max retries reached for database fixes. Will attempt to continue anyway."
fi

# Run migrations with retry logic
echo "Running migrations..."
RETRY_COUNT=0
RETRY_DELAY=2

while [ $RETRY_COUNT -lt $MAX_RETRIES ]; do
    echo "Migration attempt $((RETRY_COUNT+1))/$MAX_RETRIES"
    
    if python manage.py migrate --noinput; then
        echo "Migrations successful!"
        break
    else
        echo "Migrations failed, retrying in $RETRY_DELAY seconds..."
        RETRY_COUNT=$((RETRY_COUNT+1))
        sleep $RETRY_DELAY
        RETRY_DELAY=$((RETRY_DELAY*2))  # Exponential backoff
    fi
done

if [ $RETRY_COUNT -eq $MAX_RETRIES ]; then
    echo "WARNING: Migrations could not be completed after $MAX_RETRIES attempts."
    echo "Attempting to continue with application startup."
fi

# Collect static files
echo "Collecting static files..."
python manage.py collectstatic --noinput

# Start Telethon parser in the background
echo "Starting Telethon parser in the background..."
nohup python run_parser.py > ./parser.log 2>&1 &
echo "Telethon parser started"

# Start the Django application
echo "Starting Django application..."
exec python manage.py runserver 0.0.0.0:8080 