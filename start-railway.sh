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
chmod +x run.py
chmod +x set_bot_token.py

# Install psycopg2 explicitly to ensure database connectivity
echo "Installing psycopg2 for database connectivity..."
pip install psycopg2-binary==2.9.9
pip install psycopg2==2.9.9 || echo "Could not install psycopg2, but continuing with psycopg2-binary"

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

# Run the set_bot_token.py script to ensure the bot token is set
echo "Перевірка токену Telegram бота..."
python set_bot_token.py
if [ $? -ne 0 ]; then
  echo "⚠️ УВАГА: Перевірка токену бота не пройшла успішно!"
  echo "Для налаштування токену бота виконайте:"
  echo "python setup_bot_token.py"
else
  # Import the token from the generated file
  if [ -f "bot_token.env" ]; then
    source bot_token.env
    echo "✅ Токен бота встановлено успішно"
  fi
fi

# Debug check for essential environment variables
echo "Перевірка важливих змінних середовища:"
if [ -n "$BOT_TOKEN" ]; then
  echo "✓ BOT_TOKEN встановлено"
else
  echo "✗ BOT_TOKEN НЕ встановлено! Бот не працюватиме."
  echo "Для налаштування токену бота виконайте:"
  echo "python setup_bot_token.py"
fi

if [ -n "$DATABASE_URL" ]; then
  echo "✓ DATABASE_URL встановлено"
else
  echo "✗ DATABASE_URL НЕ встановлено!"
fi

# Ensure health check files
echo "ok" > health.txt
echo "ok" > health.html
echo "ok" > healthz.txt
echo "ok" > healthz.html

# Function to retry starting a process in case of failure
start_process_with_retry() {
    local cmd="$1"
    local log_file="$2"
    local process_name="$3"
    local max_retries=3
    local retry=0
    local pid=0
    
    while [ $retry -lt $max_retries ]; do
        echo "Starting $process_name (attempt $(($retry+1))/$max_retries)..."
        # Pass environment variables explicitly
        nohup env BOT_TOKEN="$BOT_TOKEN" DATABASE_URL="$DATABASE_URL" python $cmd > $log_file 2>&1 &
        pid=$!
        
        # Give process time to initialize
        sleep 5
        
        # Check if process is still running
        if ps -p $pid > /dev/null 2>&1; then
            echo "✓ $process_name started successfully with PID: $pid"
            echo $pid > ${process_name}.pid
            return 0
        else
            echo "✗ $process_name failed to start (attempt $(($retry+1)))"
            # Check the log for errors
            echo "--- Last 20 lines of $log_file ---"
            tail -n 20 $log_file
            echo "--- End of log excerpt ---"
            retry=$(($retry+1))
        fi
    done
    
    echo "CRITICAL: Failed to start $process_name after $max_retries attempts!"
    return 1
}

# Start the Telegram bot in background with proper logging and retry
echo "Starting Telegram bot..."
start_process_with_retry "run_bot.py" "logs/bot/bot.log" "bot"
BOT_STATUS=$?

# Start the Telegram parser in background with proper logging and retry
echo "Starting Telegram parser..."
start_process_with_retry "run_parser.py" "logs/bot/parser.log" "parser"
PARSER_STATUS=$?

# Ensure proper startup of services
if [ $BOT_STATUS -eq 0 ] && [ $PARSER_STATUS -eq 0 ]; then
    echo "All background services started successfully!"
else
    echo "WARNING: Some background services failed to start properly."
    # Try an alternative approach using run.py which can start both services
    echo "Attempting to start services using the run.py script..."
    nohup python run.py > logs/combined_services.log 2>&1 &
    RUN_PID=$!
    echo $RUN_PID > combined.pid
    echo "Combined services started with PID: $RUN_PID"
fi

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