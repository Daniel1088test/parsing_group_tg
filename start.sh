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

# Export bot-specific environment variables
export BOT_SERVER_HOST="127.0.0.1"  # Use localhost for the bot's Django server
export BOT_SERVER_PORT="8081"  # Use a different port than the main Django server

# Export important environment variables for Railway
export PUBLIC_URL="https://parsinggrouptg-production.up.railway.app"
export SECRET_KEY="/QoXhzTJkyhzSKccxR+XV0pf4T2zqLfXzPlSwegi6Cs="

# Set Telegram bot configuration from Railway variables or defaults
export BOT_TOKEN="${BOT_TOKEN:-7923260865:AAGWm7t0Zz2PqFPI5PldEVwrOC4HZ_5oP0c}"
export API_ID="${API_ID:-19840544}"
export API_HASH="${API_HASH:-c839f28bad345082329ec086fca021fa}"

# Aggressively terminate any existing bot processes
echo "Terminating any existing bot processes..."
(
  # Try to find any existing processes using our token and terminate them
  if [ -n "$BOT_TOKEN" ]; then
    if grep -r "$BOT_TOKEN" /proc/*/environ >/dev/null 2>&1; then
      echo "Found processes using our bot token, terminating..."
      for pid in $(grep -l "$BOT_TOKEN" /proc/*/environ 2>/dev/null | sed 's/\/proc\/\([0-9]*\)\/environ/\1/'); do
        if [ "$pid" != "$$" ] && [ -e "/proc/$pid" ]; then
          echo "Killing process $pid (bot token conflict)"
          kill -9 $pid >/dev/null 2>&1 || true
        fi
      done
    fi
  fi

  # Kill any Python processes that might be running bots
  for pid in $(find /proc -maxdepth 1 -name "[0-9]*" 2>/dev/null); do
    pid=$(basename $pid)
    if [ "$pid" != "$$" ] && [ -e "/proc/$pid/cmdline" ]; then
      if grep -q "python" "/proc/$pid/cmdline" 2>/dev/null && grep -q "bot.py\|run.py" "/proc/$pid/cmdline" 2>/dev/null; then
        echo "Killing Python bot process $pid"
        kill -9 $pid >/dev/null 2>&1 || true
      fi
    fi
  done
) || echo "Process cleanup failed, but continuing..."

# Clear any existing session files that might cause conflicts
echo "Clearing any existing bot sessions..."
find . -type f -name "*.session*" -delete 2>/dev/null || true
find /app -type f -name "*.session*" -delete 2>/dev/null || true

# Create necessary directories
mkdir -p /app/data
mkdir -p /app/data/messages
mkdir -p /app/data/sessions

# Wait to ensure all processes are terminated and resources released
sleep 10

echo "Starting the application..."

# Start the main application with gunicorn
gunicorn core.wsgi:application --bind 0.0.0.0:$PORT --timeout 300 --workers 2 --preload &
GUNICORN_PID=$!

# Wait for gunicorn to start
sleep 10
echo "Main application started"

# Start our bot in a separate process
cd /app
python run.py &
BOT_PID=$!
echo "Bot started (PID: $BOT_PID)"

# Wait for both processes
wait $GUNICORN_PID $BOT_PID 