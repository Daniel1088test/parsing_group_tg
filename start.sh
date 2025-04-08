#!/bin/bash

# Make script exit on any error
set -e

# Install missing packages that are critical
pip install -U dj-database-url psycopg2-binary

# Set the PORT from the environment variable or use default 8000
export PORT=${PORT:-8000}
echo "Using PORT: $PORT"

# Print all environment variables related to PostgreSQL (masked)
echo "PostgreSQL related environment variables:"
env | grep -i "PG\|DATABASE\|POSTGRES" | sed 's/\(PASSWORD\|SECRET\)=.*/\1=********/' | sort || true

# Handle Railway's PostgreSQL connection variables
if [ -z "$DATABASE_URL" ]; then
    echo "DATABASE_URL not found, attempting to construct from available variables..."
    
    # Check for all possible Railway PostgreSQL formats
    if [ ! -z "$DATABASE_PUBLIC_URL" ]; then
        export DATABASE_URL="$DATABASE_PUBLIC_URL"
        echo "Using DATABASE_PUBLIC_URL as DATABASE_URL"
    elif [ ! -z "$POSTGRES_URL" ]; then
        export DATABASE_URL="$POSTGRES_URL"
        echo "Using POSTGRES_URL as DATABASE_URL"
    elif [ ! -z "$PGHOST" ] && [ ! -z "$PGPORT" ] && [ ! -z "$PGDATABASE" ] && [ ! -z "$PGUSER" ] && [ ! -z "$PGPASSWORD" ]; then
        # Use Railway TCP Proxy for external access if available
        if [ ! -z "$RAILWAY_TCP_PROXY_DOMAIN" ] && [ ! -z "$RAILWAY_TCP_PROXY_PORT" ]; then
            export DATABASE_URL="postgresql://${PGUSER}:${PGPASSWORD}@${RAILWAY_TCP_PROXY_DOMAIN}:${RAILWAY_TCP_PROXY_PORT}/${PGDATABASE}?sslmode=require"
            echo "Constructed DATABASE_URL using Railway TCP Proxy"
        else
            # Fallback to direct connection
            export DATABASE_URL="postgresql://${PGUSER}:${PGPASSWORD}@${PGHOST}:${PGPORT}/${PGDATABASE}"
            echo "Constructed DATABASE_URL from PostgreSQL variables"
        fi
    else
        echo "WARNING: Could not find PostgreSQL variables. Using SQLite database."
        export DATABASE_URL=""
    fi
fi

# Print DATABASE_URL (with password masked)
if [ ! -z "$DATABASE_URL" ]; then
    DB_URL_MASKED=$(echo $DATABASE_URL | sed -E 's/\/\/([^:]+):([^@]+)@/\/\/\1:********@/g')
    echo "Using DATABASE_URL: $DB_URL_MASKED"

    # Extract PostgreSQL connection details
    export PGUSER=$(echo $DATABASE_URL | grep -oP '://\K[^:]+')
    export PGPASSWORD=$(echo $DATABASE_URL | grep -oP '://[^:]+:\K[^@]+')
    export PGHOST=$(echo $DATABASE_URL | grep -oP '@\K[^:]+')
    export PGPORT=$(echo $DATABASE_URL | grep -oP '@[^:]+:\K[0-9]+')
    export PGDATABASE=$(echo $DATABASE_URL | grep -oP '/\K[^?]+')

    echo "PostgreSQL connection details: host=$PGHOST, port=$PGPORT, database=$PGDATABASE, user=$PGUSER"
else
    echo "No DATABASE_URL set. Using SQLite database."
fi

# Wait for PostgreSQL to be ready if we have a connection
if [ ! -z "$DATABASE_URL" ]; then
    echo "Waiting for PostgreSQL to be ready..."
    
    # Try to connect to PostgreSQL
    max_retries=30
    retries=0
    
    until PGPASSWORD=$PGPASSWORD psql -h $PGHOST -p $PGPORT -U $PGUSER -d $PGDATABASE -c "SELECT 1" > /dev/null 2>&1; do
        retries=$((retries+1))
        if [ $retries -ge $max_retries ]; then
            echo "WARNING: PostgreSQL not available after $max_retries attempts. Continuing anyway."
            break
        fi
        echo "PostgreSQL not ready yet. Retrying in 2 seconds... (Attempt $retries/$max_retries)"
        sleep 2
    done
    
    if [ $retries -lt $max_retries ]; then
        echo "PostgreSQL is ready!"
    fi
    
    # Test database connection
    echo "Testing database connection with psql..."
    PGPASSWORD=$PGPASSWORD psql -h $PGHOST -p $PGPORT -U $PGUSER -d $PGDATABASE -c "SELECT version();" || echo "Failed to connect with psql, but continuing..."
fi

# Set Railway environment variables for the application
export RAILWAY_PUBLIC_DOMAIN="${RAILWAY_PUBLIC_DOMAIN:-parsinggrouptg-production.up.railway.app}"
export PUBLIC_URL="https://$RAILWAY_PUBLIC_DOMAIN"
echo "Setting PUBLIC_URL to $PUBLIC_URL"

# Export bot-specific environment variables from Railway
export BOT_TOKEN="${BOT_TOKEN:-7923260865:AAGWm7t0Zz2PqFPI5PldEVwrOC4HZ_5oP0c}"
export API_ID="${API_ID:-19840544}"
export API_HASH="${API_HASH:-c839f28bad345082329ec086fca021fa}"
export ADMIN_ID="${ADMIN_ID:-574349489}"
export BOT_USERNAME="${BOT_USERNAME:-@Channels_hunt_bot}"

# Create necessary directories
mkdir -p staticfiles
mkdir -p media
mkdir -p data/messages
mkdir -p data/sessions

# Run migrations (without failing if they don't work)
echo "Running migrations..."
python manage.py migrate --noinput || echo "Migrations failed, but continuing"

# Collect static files
echo "Collecting static files..."
python manage.py collectstatic --noinput || echo "Static file collection failed, but continuing"

# Check if compress command exists before running it
if python manage.py help | grep -q "compress"; then
    echo "Compressing static files..."
    python manage.py compress --force
else
    echo "Compress command not available, skipping static file compression."
fi

# Aggressively terminate any existing bot processes
echo "Terminating any existing bot processes..."
(
  # Kill any Python processes that might be running bots (but not this script)
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

echo "Starting the application..."

# Start the main application with gunicorn
gunicorn core.wsgi:application --bind 0.0.0.0:$PORT --timeout 300 --workers 2 --preload &
GUNICORN_PID=$!

# Wait for gunicorn to start
sleep 5
echo "Main application started"

# Start our bot in a separate process
cd /app
python run.py &
BOT_PID=$!
echo "Bot started (PID: $BOT_PID)"

# Wait for both processes
wait $GUNICORN_PID $BOT_PID 