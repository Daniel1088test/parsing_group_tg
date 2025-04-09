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

# Test database connection properly
echo "Testing database connection..."
python -c "import os, sys; try: import psycopg2; db_url = os.environ.get('DATABASE_URL'); print('✓ psycopg2 is properly installed'); conn = psycopg2.connect(db_url) if db_url else None; cursor = conn.cursor() if conn else None; cursor.execute('SELECT 1') if cursor else None; print('✓ Database connection successful') if cursor else print('⚠️ No DATABASE_URL provided'); cursor.close() if cursor else None; conn.close() if conn else None; except Exception as e: print(f'✗ Database error: {e}'); sys.exit(1);" || echo "Warning: Database test failed, but continuing"

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
        python fix_token.py "7923260865:AAGYew9JnOJV6hz0LGeRCb1kS6AejHoX61g" --non-interactive
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

# Deploy the bot token to all places it might be needed
python -c "
import os
import sys
try:
    token = os.environ.get('BOT_TOKEN')
    if token:
        # Update config.py
        config_path = os.path.join('tg_bot', 'config.py')
        if os.path.exists(config_path):
            with open(config_path, 'r') as f:
                lines = f.readlines()
            
            with open(config_path, 'w') as f:
                for line in lines:
                    if line.strip().startswith('TOKEN_BOT'):
                        f.write(f'TOKEN_BOT = \"{token}\"\n')
                    else:
                        f.write(line)
            print('✅ Updated config.py with token')
            
        # Update env file
        with open('bot_token.env', 'w') as f:
            f.write(f'BOT_TOKEN={token}')
        print('✅ Updated bot_token.env')
        
        # Import Django settings
        os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
        import django
        django.setup()
        
        # Update database
        from admin_panel.models import BotSettings
        bot_settings = BotSettings.objects.first()
        if bot_settings:
            bot_settings.bot_token = token
            bot_settings.save()
            print('✅ Updated token in database')
        else:
            BotSettings.objects.create(bot_token=token)
            print('✅ Created new settings in database with token')
    else:
        print('⚠️ No BOT_TOKEN in environment')
except Exception as e:
    print(f'⚠️ Error updating token: {e}')
"

# Start services in background
echo "Starting all services together..."
nohup python run.py > logs/combined_services.log 2>&1 &
COMBINED_PID=$!
echo $COMBINED_PID > combined.pid
echo "Combined services started with PID: $COMBINED_PID"

# Use existing healthcheck.py script
if [ -f "healthcheck.py" ]; then
    echo "Starting health check server..."
    nohup python healthcheck.py > logs/health.log 2>&1 &
    HEALTH_PID=$!
    echo $HEALTH_PID > health.pid
    echo "Health check server started with PID: $HEALTH_PID"
else
    echo "Warning: healthcheck.py not found, health checks may not work properly"
fi

# Give services a moment to start up
sleep 5

# Verify bot is running
ps -ef | grep -i "run_bot" | grep -v grep
if [ $? -eq 0 ]; then
    echo "✅ Bot process is running!"
else
    echo "⚠️ Bot process not detected, attempting to start it directly..."
    nohup python run_bot.py > logs/bot_direct.log 2>&1 &
    BOT_PID=$!
    echo $BOT_PID > bot_direct.pid
    echo "Direct bot process started with PID: $BOT_PID"
fi

# Start Django server in foreground (this keeps the Railway process alive)
echo "Starting Django server on 0.0.0.0:$PORT..."
exec python manage.py runserver 0.0.0.0:$PORT