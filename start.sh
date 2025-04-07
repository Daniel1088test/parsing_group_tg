#!/bin/bash

# Make script exit on any error
set -e

# Set the PORT from the environment variable or use default 8000
export PORT=${PORT:-8000}
echo "Using PORT: $PORT"

# Database settings - use these if DATABASE_URL is not set
if [ -z "$DATABASE_URL" ]; then
    echo "WARNING: DATABASE_URL not found, checking for Railway PostgreSQL service..."
    
    # Check if Railway PostgreSQL variables are available
    if [ ! -z "$PGHOST" ] && [ ! -z "$PGPORT" ] && [ ! -z "$PGDATABASE" ] && [ ! -z "$PGUSER" ] && [ ! -z "$PGPASSWORD" ]; then
        echo "Found Railway PostgreSQL environment variables, constructing DATABASE_URL..."
        export DATABASE_URL="postgresql://${PGUSER}:${PGPASSWORD}@${PGHOST}:${PGPORT}/${PGDATABASE}?sslmode=require"
        echo "DATABASE_URL constructed from Railway PostgreSQL service variables."
    else
        echo "WARNING: No PostgreSQL environment variables found. Using fallback value."
        echo "This should not happen in production. Make sure to set DATABASE_URL in Railway dashboard!"
        export DATABASE_URL="postgresql://postgres:urCNhXdwvbqOvvEsJDffIiDUMcLhAvcs@switchback.proxy.rlwy.net:10052/railway?sslmode=require"
    fi
fi

# Wait for PostgreSQL to be ready
wait_for_postgres() {
    echo "Waiting for PostgreSQL to be ready..."
    
    # Extract connection details from DATABASE_URL
    PGUSER=$(echo $DATABASE_URL | awk -F '//' '{print $2}' | awk -F ':' '{print $1}')
    PGPASSWORD=$(echo $DATABASE_URL | awk -F ':' '{print $3}' | awk -F '@' '{print $1}')
    PGHOST=$(echo $DATABASE_URL | awk -F '@' '{print $2}' | awk -F ':' '{print $1}')
    PGPORT=$(echo $DATABASE_URL | awk -F ':' '{print $4}' | awk -F '/' '{print $1}')
    PGDATABASE=$(echo $DATABASE_URL | awk -F '/' '{print $4}' | awk -F '?' '{print $1}')
    
    export PGPASSWORD=$PGPASSWORD
    
    # Try to connect to PostgreSQL with a timeout
    max_retries=30
    retries=0
    
    until pg_isready -h $PGHOST -p $PGPORT -U $PGUSER -d $PGDATABASE; do
        retries=$((retries+1))
        if [ $retries -ge $max_retries ]; then
            echo "ERROR: PostgreSQL not available after $max_retries attempts. Exiting."
            exit 1
        fi
        echo "PostgreSQL not ready yet. Retrying in 2 seconds... (Attempt $retries/$max_retries)"
        sleep 2
    done
    
    echo "PostgreSQL is ready!"
}

# Set up web server host and port for Django
export WEB_SERVER_HOST="0.0.0.0"  # Listen on all interfaces
export WEB_SERVER_PORT="$PORT"
export DJANGO_SETTINGS_MODULE=core.settings

# Set the PUBLIC_URL variable if running on Railway
if [ -z "$PUBLIC_URL" ]; then
    if [ ! -z "$RAILWAY_STATIC_URL" ]; then
        export PUBLIC_URL="$RAILWAY_STATIC_URL"
        echo "Setting PUBLIC_URL to $PUBLIC_URL from RAILWAY_STATIC_URL"
    elif [ ! -z "$RAILWAY_PUBLIC_DOMAIN" ]; then
        export PUBLIC_URL="https://$RAILWAY_PUBLIC_DOMAIN"
        echo "Setting PUBLIC_URL to $PUBLIC_URL from RAILWAY_PUBLIC_DOMAIN"
    else
        export PUBLIC_URL="https://parsinggrouptg-production.up.railway.app"
        echo "Setting PUBLIC_URL to default value: $PUBLIC_URL"
    fi
else
    echo "Using existing PUBLIC_URL: $PUBLIC_URL"
fi

# Create necessary directories
mkdir -p staticfiles
mkdir -p media

# Wait for PostgreSQL to be ready
wait_for_postgres

# Database backup/restore handling for persistence
if [ -n "$DATABASE_URL" ]; then
    echo "Setting up database persistence..."
    BACKUP_DIR="/app/db_backups"
    mkdir -p $BACKUP_DIR

    # Extract database credentials from DATABASE_URL
    PGUSER=$(echo $DATABASE_URL | awk -F '//' '{print $2}' | awk -F ':' '{print $1}')
    PGPASSWORD=$(echo $DATABASE_URL | awk -F ':' '{print $3}' | awk -F '@' '{print $1}')
    PGHOST=$(echo $DATABASE_URL | awk -F '@' '{print $2}' | awk -F ':' '{print $1}')
    PGPORT=$(echo $DATABASE_URL | awk -F ':' '{print $4}' | awk -F '/' '{print $1}')
    PGDATABASE=$(echo $DATABASE_URL | awk -F '/' '{print $4}' | awk -F '?' '{print $1}')

    # Check if backup file exists and restore if it does
    export PGPASSWORD=$PGPASSWORD
    if [ -f "$BACKUP_DIR/db_backup.sql" ]; then
        echo "Restoring database from backup..."
        pg_restore -h $PGHOST -p $PGPORT -U $PGUSER -d $PGDATABASE -c "$BACKUP_DIR/db_backup.sql" || true
    fi

    # Create backup hook for when the app shuts down
    create_backup() {
        echo "Creating database backup before shutdown..."
        pg_dump -h $PGHOST -p $PGPORT -U $PGUSER -d $PGDATABASE -F c -f "$BACKUP_DIR/db_backup.sql" || true
        echo "Backup completed."
    }

    # Register the trap
    trap create_backup SIGTERM SIGINT
fi

# Run migrations
echo "Running migrations..."
python manage.py migrate --noinput

# Collect static files
echo "Collecting static files..."
python manage.py collectstatic --noinput

# Compress files if needed
if [ -x "$(command -v python manage.py compress)" ]; then
    echo "Compressing static files..."
    python manage.py compress --force
fi

# Create superuser if needed
if [ -n "$DJANGO_SUPERUSER_USERNAME" ] && [ -n "$DJANGO_SUPERUSER_PASSWORD" ] && [ -n "$DJANGO_SUPERUSER_EMAIL" ]; then
    echo "Creating superuser..."
    python manage.py createsuperuser --noinput || true
fi

# Start server
echo "Starting server..."
gunicorn core.asgi:application -k uvicorn.workers.UvicornWorker --bind 0.0.0.0:$PORT --timeout 120 --workers 2 &
GUNICORN_PID=$!

# Start background tasks (in this case the Telegram bot)
echo "Starting Telegram bot..."
python run.py &
TELEGRAM_PID=$!

# Wait for all processes
wait $GUNICORN_PID $TELEGRAM_PID 