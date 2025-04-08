#!/bin/bash
set -e

echo "===================== Starting Railway Deployment ====================="

# Export needed environment variables 
echo "Setting up environment variables..."
export RAILWAY_PUBLIC_DOMAIN=${RAILWAY_PUBLIC_DOMAIN:-"parsinggrouptg-production.up.railway.app"}
export PORT=${PORT:-8080}

# Fix requirements.txt if needed (додатковий рівень захисту)
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

# Run our enhanced migration script that handles errors and prepares media paths
echo "Running enhanced migration script..."
python migrate-railway.py

# Extra safety measure: check if media directories exist
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

# Ensure health check files
echo "ok" > health.txt
echo "ok" > health.html
echo "ok" > healthz.txt
echo "ok" > healthz.html

# Start the Telegram bot in background with proper logging
echo "Starting Telegram bot in background..."
nohup python run_bot.py > logs/bot/bot.log 2>&1 &
BOT_PID=$!
echo "Bot started with PID: $BOT_PID"

# Start the Telegram parser in background with proper logging
echo "Starting Telegram parser in background..."
nohup python run_parser.py > logs/bot/parser.log 2>&1 &
PARSER_PID=$!
echo "Parser started with PID: $PARSER_PID"

# Give the background processes a moment to start and check if they're running
sleep 2

# Check if processes are running - with fallback for systems without ps
if command -v ps >/dev/null 2>&1; then
    # ps command exists
    ps -p $BOT_PID >/dev/null && echo "Bot is running correctly" || echo "Warning: Bot may have failed to start"
    ps -p $PARSER_PID >/dev/null && echo "Parser is running correctly" || echo "Warning: Parser may have failed to start"
else
    # ps command doesn't exist - alternative check using /proc on Linux
    if [ -d "/proc/$BOT_PID" ]; then
        echo "Bot is running correctly"
    else
        echo "Warning: Bot may have failed to start"
    fi
    
    if [ -d "/proc/$PARSER_PID" ]; then
        echo "Parser is running correctly"
    else
        echo "Warning: Parser may have failed to start"
    fi
fi

# Create PID files for service monitoring
echo $BOT_PID > bot.pid
echo $PARSER_PID > parser.pid

# Use existing healthcheck.py instead of creating it inline
if [ -f "healthcheck.py" ]; then
    echo "Using existing healthcheck.py"
    chmod +x healthcheck.py
    nohup python healthcheck.py > logs/health.log 2>&1 &
    HEALTH_PID=$!
    echo "Health check server started with PID: $HEALTH_PID"
else
    echo "Warning: healthcheck.py not found, health checks may not work properly"
fi

# Start the Django server
echo "Starting Django server on 0.0.0.0:$PORT..."
exec python manage.py runserver 0.0.0.0:$PORT