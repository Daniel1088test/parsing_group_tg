#!/bin/bash
set -e

echo "===================== Starting Railway Deployment ====================="

# Export needed environment variables 
echo "Setting up environment variables..."
export RAILWAY_PUBLIC_DOMAIN=${RAILWAY_PUBLIC_DOMAIN:-"parsinggrouptg-production.up.railway.app"}
export PORT=${PORT:-8080}

# Add a check to see if BOT_TOKEN exists in environment, and if not, load from bot_token.env
if [ -z "$BOT_TOKEN" ]; then
  if [ -f "bot_token.env" ]; then
    echo "Loading BOT_TOKEN from bot_token.env file..."
    source bot_token.env
  fi
fi

# Fix requirements.txt if needed
echo "Checking requirements.txt for conflicts..."
if [ -f "fix_requirements.py" ]; then
    python fix_requirements.py
    if [ $? -ne 0 ]; then
        echo "Warning: Could not fix requirements.txt, but continuing"
    else
        echo "Requirements check completed"
    fi
fi

# Make scripts executable
chmod +x migrate-railway.py
chmod +x run_bot.py
chmod +x run_parser.py
chmod +x run.py
chmod +x set_bot_token.py
chmod +x fix_token.py

# Install essential PostgreSQL dependencies 
echo "Installing PostgreSQL dependencies..."
pip install psycopg2-binary==2.9.9 --no-cache-dir
pip install psycopg2==2.9.9 --no-cache-dir || echo "Could not install psycopg2, but continuing with psycopg2-binary"

# Test database connection properly
echo "Testing database connection..."
python -c "
import os, sys
try:
    import psycopg2
    db_url = os.environ.get('DATABASE_URL')
    if db_url:
        print('Connecting to database...')
        conn = psycopg2.connect(db_url)
        cursor = conn.cursor()
        cursor.execute('SELECT 1')
        print('✓ Database connection successful')
        cursor.close()
        conn.close()
    else:
        print('✗ DATABASE_URL not set!')
        sys.exit(1)
except Exception as e:
    print(f'✗ Database connection error: {str(e)}')
    sys.exit(1)
"

if [ $? -ne 0 ]; then
    echo "⚠️ WARNING: Database connection test failed! Will continue but service may not work correctly"
else
    echo "✅ Database connection verified successfully"
fi

# Run enhanced migration script for Railway
echo "Running migrations with enhanced error handling..."
python migrate-railway.py

# Ensure media directories exist
echo "Ensuring media directories exist..."
mkdir -p media/messages
mkdir -p staticfiles/media
mkdir -p logs/bot
mkdir -p data/sessions

# Set directory permissions
echo "Setting directory permissions..."
chmod -R 755 media
chmod -R 755 staticfiles
chmod -R 755 logs
chmod -R 755 data

# Print environment information
echo "Environment information:"
echo "PORT: $PORT"
echo "RAILWAY_PUBLIC_DOMAIN: $RAILWAY_PUBLIC_DOMAIN"
echo "PUBLIC_URL: $PUBLIC_URL"

# Check and fix token if not set
if [ -z "$BOT_TOKEN" ]; then
    echo "⚠️ BOT_TOKEN not set! Attempting to configure it..."
    
    # First try getting it from config.py
    BOT_TOKEN=$(python -c "
try:
    import sys, os, django
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
    django.setup()
    from tg_bot.config import TOKEN_BOT
    print(TOKEN_BOT)
except Exception as e:
    print('')
")

    if [ -z "$BOT_TOKEN" ]; then
        echo "No BOT_TOKEN in config.py. Attempting to run fix_token.py..."
        # Run automated token setup with the token from command line argument
        python fix_token.py "7923260865:AAGYew9JnOJV6hz0LGeRCb1kS6AejHoX61g"
        # Source the new token
        if [ -f "bot_token.env" ]; then
            source bot_token.env
            echo "✅ Token updated from fix_token.py script"
        fi
    else
        echo "✅ Using TOKEN_BOT from config.py: $BOT_TOKEN"
        export BOT_TOKEN
    fi
fi

# Verify bot token is set
if [ -z "$BOT_TOKEN" ]; then
    echo "❌ CRITICAL: BOT_TOKEN still not set after all attempts!"
    echo "The bot will not function correctly!"
else
    echo "✅ BOT_TOKEN is set and ready to use"
fi

# Ensure health check files
echo "ok" > health.txt
echo "ok" > health.html
echo "ok" > healthz.txt
echo "ok" > healthz.html

# Run our combined launcher that manages bot + parser together
echo "Starting all services together..."
python run.py &
COMBINED_PID=$!
echo $COMBINED_PID > combined.pid
echo "Combined services started with PID: $COMBINED_PID"

# Use existing healthcheck.py script
if [ -f "healthcheck.py" ]; then
    echo "Starting health check server..."
    python healthcheck.py > logs/health.log 2>&1 &
    HEALTH_PID=$!
    echo "Health check server started with PID: $HEALTH_PID"
else
    echo "Warning: healthcheck.py not found, health checks may not work properly"
fi

# Start Django server in foreground (this keeps the Railway process alive)
echo "Starting Django server on 0.0.0.0:$PORT..."
exec python manage.py runserver 0.0.0.0:$PORT