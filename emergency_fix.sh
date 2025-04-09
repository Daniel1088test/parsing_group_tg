#!/bin/bash
# Emergency fix script to address deployment issues

echo "===== EMERGENCY DEPLOYMENT FIX v1.0 ====="
echo "Current time: $(date)"

# Kill any existing bot processes to start fresh
echo "Stopping existing bot processes..."
pkill -f "run_bot.py" || echo "No run_bot.py processes found"
pkill -f "python.*bot\.py" || echo "No bot.py processes found"
pkill -f "direct_bot" || echo "No direct_bot processes found"
pkill -f "emergency_bot" || echo "No emergency_bot processes found"
sleep 2

# Check and create necessary directories
echo "Ensuring required directories exist..."
mkdir -p logs/bot media/messages staticfiles/media data/sessions

# Create simple health endpoints
echo "Creating health check endpoints..."
echo "ok" > health.txt
echo "ok" > healthz.txt
echo "ok" > health.html
echo "ok" > healthz.html
echo "Health checks created"

# Force Django migrations
echo "Forcing database migrations..."
export DJANGO_SETTINGS_MODULE=core.settings
python -c "
import os, sys, django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()
try:
    # Just check if we can connect to DB
    from django.db import connection
    with connection.cursor() as cursor:
        cursor.execute('SELECT 1')
        print('✓ Database connection verified')
        
    # Manual check and fix for BotSettings table
    try:
        cursor.execute(\"\"\"
            CREATE TABLE IF NOT EXISTS admin_panel_botsettings (
                id SERIAL PRIMARY KEY,
                bot_token VARCHAR(255) NOT NULL,
                bot_username VARCHAR(255) NULL,
                welcome_message TEXT NULL,
                auth_guide_text TEXT NULL,
                menu_style VARCHAR(50) NULL
            )
        \"\"\")
        print('✓ BotSettings table check/creation completed')
    except Exception as e:
        print(f'Error creating BotSettings table: {e}')
        
    # Check if we have BotSettings and create if needed
    token = os.environ.get('BOT_TOKEN', '7923260865:AAGYew9JnOJV6hz0LGeRCb1kS6AejHoX61g')
    
    cursor.execute('SELECT COUNT(*) FROM admin_panel_botsettings')
    count = cursor.fetchone()[0]
    if count == 0:
        print('Creating BotSettings record...')
        cursor.execute(\"\"\"
            INSERT INTO admin_panel_botsettings (bot_token, bot_username, menu_style)
            VALUES (%s, %s, 'default')
        \"\"\", [token, 'Channels_hunt_bot'])
        print('✓ Created BotSettings record')
    else:
        print('✓ BotSettings record exists')
        
    from django.core.management import call_command
    call_command('migrate', interactive=False)
    print('✓ Django migrations applied')
except Exception as e:
    print(f'❌ Database error: {e}')
"

# Run the bot directly (best chance of success)
echo "Starting bot directly..."
nohup python run_bot.py > logs/bot/emergency_direct.log 2>&1 &
DIRECT_PID=$!
echo $DIRECT_PID > emergency_direct.pid
echo "Direct bot started with PID: $DIRECT_PID"

# Wait a moment to let the bot initialize
sleep 5

# Check if bot is running
if ps -p $DIRECT_PID > /dev/null; then
    echo "✅ Bot process is still running after 5 seconds"
else
    echo "❌ Bot process exited - check logs"
    tail -n 20 logs/bot/emergency_direct.log
fi

echo "===== EMERGENCY FIX COMPLETED ====="
echo "Current time: $(date)"
echo "Run the following command to see bot logs: tail -f logs/bot/emergency_direct.log" 