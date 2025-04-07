#!/bin/bash

# Make script exit on any error
set -e

# Set the PORT from the environment variable or use default 8000
export PORT=${PORT:-8000}
echo "Using PORT: $PORT"

# Print all environment variables related to PostgreSQL (masked)
echo "PostgreSQL related environment variables:"
env | grep -i "PG\|DATABASE\|POSTGRES" | sed 's/\(PASSWORD\|SECRET\)=.*/\1=********/' | sort || true

# Database settings - use these if DATABASE_URL is not set
if [ -z "$DATABASE_URL" ]; then
    echo "WARNING: DATABASE_URL not found, checking for Railway PostgreSQL service..."
    
    # Check for Railway service variables - try all possible formats
    if [ ! -z "$POSTGRES_URL" ]; then
        export DATABASE_URL="$POSTGRES_URL"
        echo "Found POSTGRES_URL, using it as DATABASE_URL"
    elif [ ! -z "$POSTGRES_CONNECTION_URL" ]; then
        export DATABASE_URL="$POSTGRES_CONNECTION_URL"
        echo "Found POSTGRES_CONNECTION_URL, using it as DATABASE_URL"
    elif [ ! -z "$PGHOST" ] && [ ! -z "$PGPORT" ] && [ ! -z "$PGDATABASE" ] && [ ! -z "$PGUSER" ] && [ ! -z "$PGPASSWORD" ]; then
        echo "Found Railway PostgreSQL environment variables, constructing DATABASE_URL..."
        export DATABASE_URL="postgresql://${PGUSER}:${PGPASSWORD}@${PGHOST}:${PGPORT}/${PGDATABASE}?sslmode=require"
        echo "DATABASE_URL constructed from Railway PostgreSQL service variables."
    else
        echo "WARNING: No PostgreSQL environment variables found. Checking for plugin-provided variables..."
        
        # Check if Railway Postgres plugin provided variables
        if printenv | grep -q "RAILWAY_"; then
            echo "Found Railway environment. Attempting to discover PostgreSQL variables..."
            printenv | grep "RAILWAY_" | sort
        fi
        
        echo "Using fallback DATABASE_URL. THIS SHOULD NOT HAPPEN IN PRODUCTION."
        echo "Please configure the PostgreSQL plugin or set DATABASE_URL in Railway dashboard!"
        
        # Use a fallback value, but it should be configured correctly in production
        export DATABASE_URL="postgresql://postgres:urCNhXdwvbqOvvEsJDffIiDUMcLhAvcs@switchback.proxy.rlwy.net:10052/railway?sslmode=require"
    fi
fi

# Print DATABASE_URL (with password masked)
DB_URL_MASKED=$(echo $DATABASE_URL | sed -E 's/\/\/([^:]+):([^@]+)@/\/\/\1:********@/g')
echo "Using DATABASE_URL: $DB_URL_MASKED"

# Extract and set standard PostgreSQL environment variables from DATABASE_URL
# This helps with standard PostgreSQL tools
if [ -n "$DATABASE_URL" ]; then
    export PGUSER=$(echo $DATABASE_URL | awk -F '//' '{print $2}' | awk -F ':' '{print $1}')
    export PGPASSWORD=$(echo $DATABASE_URL | awk -F ':' '{print $3}' | awk -F '@' '{print $1}')
    export PGHOST=$(echo $DATABASE_URL | awk -F '@' '{print $2}' | awk -F ':' '{print $1}')
    export PGPORT=$(echo $DATABASE_URL | awk -F ':' '{print $4}' | awk -F '/' '{print $1}')
    export PGDATABASE=$(echo $DATABASE_URL | awk -F '/' '{print $4}' | awk -F '?' '{print $1}')
    echo "PostgreSQL connection details extracted: host=$PGHOST, port=$PGPORT, database=$PGDATABASE, user=$PGUSER"
fi

# Wait for PostgreSQL to be ready
wait_for_postgres() {
    echo "Waiting for PostgreSQL to be ready..."
    
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

# Test database connection directly using psql
echo "Testing database connection with psql..."
PGPASSWORD=$PGPASSWORD psql -h $PGHOST -p $PGPORT -U $PGUSER -d $PGDATABASE -c "SELECT version();" || echo "Failed to connect with psql, but continuing..."

# Database backup/restore handling for persistence
if [ -n "$DATABASE_URL" ]; then
    echo "Setting up database persistence..."
    BACKUP_DIR="/app/db_backups"
    mkdir -p $BACKUP_DIR

    # Check if backup file exists and restore if it does
    if [ -f "$BACKUP_DIR/db_backup.sql" ]; then
        echo "Restoring database from backup..."
        PGPASSWORD=$PGPASSWORD pg_restore -h $PGHOST -p $PGPORT -U $PGUSER -d $PGDATABASE -c "$BACKUP_DIR/db_backup.sql" || true
    fi

    # Create backup hook for when the app shuts down
    create_backup() {
        echo "Creating database backup before shutdown..."
        PGPASSWORD=$PGPASSWORD pg_dump -h $PGHOST -p $PGPORT -U $PGUSER -d $PGDATABASE -F c -f "$BACKUP_DIR/db_backup.sql" || true
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

# Check if compress command exists before running it
if python manage.py help | grep -q "compress"; then
    echo "Compressing static files..."
    python manage.py compress --force
else
    echo "Compress command not available, skipping static file compression."
fi

# Create superuser if needed
if [ -n "$DJANGO_SUPERUSER_USERNAME" ] && [ -n "$DJANGO_SUPERUSER_PASSWORD" ] && [ -n "$DJANGO_SUPERUSER_EMAIL" ]; then
    echo "Creating superuser..."
    python manage.py createsuperuser --noinput || true
fi

# Start server
echo "Starting server..."
if command -v gunicorn &> /dev/null; then
    gunicorn core.wsgi:application --bind 0.0.0.0:$PORT --timeout 120 --workers 2 &
    GUNICORN_PID=$!
else
    echo "Gunicorn not found, using Django development server..."
    python manage.py runserver 0.0.0.0:$PORT &
    GUNICORN_PID=$!
fi

# Start background tasks (in this case the Telegram bot)
echo "Starting Telegram bot..."

# Kill any existing Python processes running the bot
echo "Checking for existing bot processes..."
ps aux | grep "[p]ython.*run.py" | awk '{print $2}' | xargs -r kill -9 || true
sleep 5  # Give more time for process cleanup

# Clear any existing session files that might cause conflicts
echo "Clearing any existing bot sessions..."
rm -f *.session* || true
sleep 2

# Start the bot with a fresh session
echo "Starting fresh bot instance..."
python run.py &
TELEGRAM_PID=$!

# Wait for all processes
wait $GUNICORN_PID $TELEGRAM_PID 