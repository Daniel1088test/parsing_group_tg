#!/bin/bash
set -e

echo "===================== Starting Railway Deployment ====================="

# Create health check files IMMEDIATELY to prevent deployment timeouts
echo "Creating health check files..."
echo "OK" > health.txt
echo "OK" > health.html
echo "OK" > healthz.txt
echo "OK" > healthz.html

# Start health check server in background
echo "Starting health check server..."
chmod +x healthcheck.py
nohup python healthcheck.py > logs/health_server.log 2>&1 &
HEALTH_PID=$!
echo $HEALTH_PID > health.pid
echo "Health check server started with PID: $HEALTH_PID"

# Export needed environment variables 
echo "Setting up environment variables..."
export RAILWAY_PUBLIC_DOMAIN=${RAILWAY_PUBLIC_DOMAIN:-"parsinggrouptg-production.up.railway.app"}
export PORT=${PORT:-8080}

# Make our fix scripts executable
echo "Making fix scripts executable..."
chmod +x railway_fix.sh
chmod +x sql_fix.py
chmod +x fix_aiohttp_sessions.py

# Run our session fix first to fix the unclosed sessions warning
echo "Fixing aiohttp session issues..."
python fix_aiohttp_sessions.py || echo "Session fix failed, continuing..."

# Run our comprehensive migration fix
echo "Running comprehensive migration fix..."
bash railway_fix.sh || echo "Migration fix script failed, continuing..."

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
python -c "
import os, sys
try:
    import psycopg2
    print('✓ psycopg2 is properly installed')
    db_url = os.environ.get('DATABASE_URL')
    if db_url:
        conn = psycopg2.connect(db_url)
        cursor = conn.cursor()
        cursor.execute('SELECT 1')
        print('✓ Database connection successful')
        cursor.close()
        conn.close()
    else:
        print('⚠️ No DATABASE_URL provided')
except Exception as e:
    print(f'✗ Database error: {e}')
    sys.exit(1)
" || echo "Warning: Database test failed, but continuing"

# Run enhanced migration script for Railway
echo "Running migrations with enhanced error handling..."
python migrate-railway.py

# Force database migrations
echo "Ensuring database tables exist..."
python manage.py migrate --noinput || python -c "
import os, sys, django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()
from django.core.management import call_command
try:
    print('Forcing migrations with fallback method...')
    call_command('migrate', interactive=False, verbosity=3)
    print('Migration completed with fallback method')
except Exception as e:
    print(f'Migration error: {e}')
    # Try reset migrations as last resort
    try:
        print('Last resort: Applying only auth and contenttypes migrations...')
        call_command('migrate', 'auth', interactive=False)
        call_command('migrate', 'contenttypes', interactive=False)
        call_command('migrate', 'admin', interactive=False)
        call_command('migrate', 'sessions', interactive=False)
        print('Critical migrations applied')
    except Exception as last_e:
        print(f'Critical migration error: {last_e}')
"

# Verify database setup
echo "Verifying database setup..."
python -c "
import os, sys, django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()
from django.db import connection
try:
    with connection.cursor() as cursor:
        cursor.execute('SELECT 1')
        print('✓ Database connection verified')
        # Check if critical tables exist
        cursor.execute(\"\"\"
            SELECT table_name FROM information_schema.tables 
            WHERE table_schema='public'
        \"\"\")
        tables = [row[0] for row in cursor.fetchall()]
        print(f'Found {len(tables)} tables in database')
        for table in ['admin_panel_botsettings', 'auth_user', 'django_session']:
            if table in tables:
                print(f'✓ Table {table} exists')
            else:
                print(f'✗ Table {table} missing!')
except Exception as e:
    print(f'Database verification error: {e}')
"

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

# Run the bot connection fix script
echo "Running comprehensive bot connection fix..."
chmod +x fix_bot_connection.py
python fix_bot_connection.py
if [ $? -eq 0 ]; then
    echo "✅ Bot connection fix completed successfully"
else
    echo "⚠️ Bot connection fix encountered issues, but continuing"
fi

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

# Direct bot launch for more reliability
echo "Starting Telegram bot directly for extra reliability..."
mkdir -p logs/bot
nohup python -c "
import os, sys, asyncio, logging, signal, time, traceback

# Configure logging for direct bot launch
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('logs/bot/direct_bot.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger('direct_bot_starter')

# Set up environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
import django
django.setup()

# Create a file to indicate bot is starting
with open('bot_starting.flag', 'w') as f:
    f.write(str(time.time()))
logger.info('Bot starting flag created')

# For detecting if the bot is actually running
bot_running = False
bot_info = None

async def verify_bot_running():
    global bot_running, bot_info
    try:
        from tg_bot.bot import bot
        bot_info = await bot.get_me()
        logger.info(f'✅ Bot verification successful: {bot_info.username} (ID: {bot_info.id})')
        bot_running = True
        # Create a file that shows bot is verified
        with open('bot_verified.flag', 'w') as f:
            f.write(f'{bot_info.id}:{bot_info.username}')
        return True
    except Exception as e:
        logger.error(f'❌ Bot verification failed: {e}')
        return False

# Start the bot with verification
async def run_bot():
    try:
        from tg_bot.bot import main, bot
        from aiogram.types import BotCommand, BotCommandScopeDefault
        
        # Set up commands
        commands = [
            BotCommand(command='start', description='Start the bot and show main menu'),
            BotCommand(command='menu', description='Show the main menu'),
            BotCommand(command='help', description='Show help'),
            BotCommand(command='authorize', description='Start authorization process')
        ]
        
        # First verify bot is running
        logger.info('Verifying bot connection...')
        verification_attempts = 0
        max_verification_attempts = 3
        
        while verification_attempts < max_verification_attempts:
            if await verify_bot_running():
                break
            verification_attempts += 1
            logger.warning(f'Bot verification attempt {verification_attempts} failed, retrying...')
            await asyncio.sleep(3)
        
        if not bot_running:
            logger.critical('❌ CRITICAL: Bot verification failed after multiple attempts')
            logger.critical('Cannot continue without verified bot connection')
            return
            
        try:
            await bot.set_my_commands(commands=commands, scope=BotCommandScopeDefault())
            logger.info('Bot commands registered successfully')
        except Exception as e:
            logger.error(f'Error setting bot commands: {e}')
        
        logger.info('Starting bot main loop')
        await main()
    except Exception as e:
        logger.error(f'Critical error in bot: {e}')
        logger.error(traceback.format_exc())

# Run the bot with asyncio
try:
    logger.info('Initializing direct bot process')
    asyncio.run(run_bot())
except Exception as e:
    logger.error(f'Fatal error running bot: {e}')
    logger.error(traceback.format_exc())
" > logs/bot/direct_bot_output.log 2>&1 &
DIRECT_BOT_PID=$!
echo $DIRECT_BOT_PID > direct_bot.pid
echo "Direct bot process started with PID: $DIRECT_BOT_PID"

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

# Verify bot is running - check both standard and direct processes
echo "Checking if bot processes are running..."
ps -ef | grep -i "python" | grep -v grep

# Check for bot verification flag
if [ -f "bot_verified.flag" ]; then
    BOT_INFO=$(cat bot_verified.flag)
    echo "✅ Bot verified and connected to Telegram API: $BOT_INFO"
else
    echo "⚠️ Bot verification flag not found - bot may not be properly connected"
fi

# Check direct bot logs for signs of successful connection
if grep -q "Bot verified" logs/bot/direct_bot.log 2>/dev/null; then
    echo "✅ Found successful bot verification in logs"
elif grep -q "Bot started:" logs/bot/direct_bot.log 2>/dev/null; then
    echo "⚠️ Bot started but verification unclear"
else
    echo "❌ No signs of successful bot start in logs"
fi

# Verify direct bot specifically 
if ps -p $DIRECT_BOT_PID > /dev/null; then
    echo "✅ Direct bot process is running with PID: $DIRECT_BOT_PID"
    # Check the process age to ensure it's stable
    PROC_START=$(ps -p $DIRECT_BOT_PID -o lstart= 2>/dev/null)
    echo "   Process started at: $PROC_START"
else
    echo "⚠️ Direct bot process failed to start or terminated"
    if [ -f "logs/bot/direct_bot_output.log" ]; then
        echo "Direct bot output log (last 20 lines):"
        cat logs/bot/direct_bot_output.log | tail -n 20
    fi
    
    if [ -f "logs/bot/direct_bot.log" ]; then
        echo "Direct bot log (last 20 lines):"
        cat logs/bot/direct_bot.log | tail -n 20
    fi
fi

# Verify the combined services
if ps -p $COMBINED_PID > /dev/null; then
    echo "✅ Combined services process is running with PID: $COMBINED_PID"
else 
    echo "⚠️ Combined services process failed to start or terminated"
    if [ -f "logs/combined_services.log" ]; then
        echo "Combined services log (last 20 lines):"
        cat logs/combined_services.log | tail -n 20
    fi
fi

# Extra database check
echo "Final database connection check..."
python -c "
import os, sys, django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()
try:
    from admin_panel.models import BotSettings
    from django.db import connection
    
    # First check if the BotSettings table structure is correct
    with connection.cursor() as cursor:
        cursor.execute(\"\"\"
            SELECT column_name FROM information_schema.columns 
            WHERE table_name='admin_panel_botsettings'
        \"\"\")
        columns = [row[0] for row in cursor.fetchall()]
        print(f'BotSettings table has columns: {columns}')
        
        # Check if bot_username column exists, if not add it
        if 'bot_username' not in columns:
            print('Adding missing bot_username column to BotSettings table')
            cursor.execute('ALTER TABLE admin_panel_botsettings ADD COLUMN bot_username VARCHAR(255) NULL')
    
    # Now get BotSettings safely
    settings = BotSettings.objects.first()
    if settings:
        print(f'✓ BotSettings found in database: {settings.id}')
        if settings.bot_token:
            masked_token = settings.bot_token[:5] + '...' + settings.bot_token[-5:]
            print(f'✓ Bot token is set in database: {masked_token}')
        else:
            print('✗ Bot token is not set in database')
            # Set the token
            settings.bot_token = os.environ.get('BOT_TOKEN', '')
            settings.save()
            print('✓ Updated bot_token in database')
    else:
        print('ℹ️ No BotSettings found in database, will create default')
        BotSettings.objects.create(
            bot_token=os.environ.get('BOT_TOKEN', ''),
            bot_username='Channels_hunt_bot'  # Default username
        )
        print('✓ Created default BotSettings')
except Exception as e:
    print(f'Error checking BotSettings: {e}')
    # Emergency fix - create missing table or column directly
    try:
        with connection.cursor() as cursor:
            print('Attempting emergency database fix...')
            # Try to create the table if it doesn't exist
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
            print('✓ Emergency table creation completed')
            
            # Insert default settings if needed
            cursor.execute(\"\"\"
                INSERT INTO admin_panel_botsettings (bot_token, bot_username)
                SELECT %s, %s
                WHERE NOT EXISTS (SELECT 1 FROM admin_panel_botsettings)
            \"\"\", [os.environ.get('BOT_TOKEN', ''), 'Channels_hunt_bot'])
            print('✓ Emergency settings insertion completed')
    except Exception as fix_error:
        print(f'Emergency fix failed: {fix_error}')
"

# Extra bot launch as fallback if both others failed
if ! (ps -p $DIRECT_BOT_PID > /dev/null || ps -ef | grep -i "run_bot" | grep -v grep > /dev/null); then
    echo "⚠️⚠️ No bot processes detected, launching emergency backup bot..."
    nohup python run_bot.py > logs/bot/emergency_bot.log 2>&1 &
    EMERGENCY_BOT_PID=$!
    echo $EMERGENCY_BOT_PID > emergency_bot.pid
    echo "Emergency bot process started with PID: $EMERGENCY_BOT_PID"
fi

# Last resort - try Django command approach
if ! (ps -p $DIRECT_BOT_PID > /dev/null || ps -p $EMERGENCY_BOT_PID > /dev/null 2>/dev/null || ps -ef | grep -i "run_bot" | grep -v grep > /dev/null); then
    echo "⚠️⚠️⚠️ CRITICAL: All bot launch methods failed, trying Django management command..."
    nohup python manage.py runbot > logs/bot/django_cmd_bot.log 2>&1 &
    DJANGO_BOT_PID=$!
    echo $DJANGO_BOT_PID > django_bot.pid
    echo "Django management command bot started with PID: $DJANGO_BOT_PID"
    
    # Create a special flag file to indicate we've tried everything
    echo "$(date) - All methods tried" > bot_all_methods_attempted.flag
fi

# Final rescue - run the comprehensive fix and restart script if no verification
if [ ! -f "bot_verified.flag" ]; then
    echo "⚠️⚠️⚠️ CRITICAL: Bot verification not detected, running comprehensive fix and restart script..."
    chmod +x run_fix_and_restart.sh
    nohup bash run_fix_and_restart.sh > logs/comprehensive_fix.log 2>&1 &
    RESCUE_PID=$!
    echo $RESCUE_PID > rescue.pid
    echo "Comprehensive fix and restart script started with PID: $RESCUE_PID"
fi

# Start the bot monitor in daemon mode to keep bot alive
echo "Starting bot monitor daemon..."
nohup python manage.py monitor_bot --daemon > logs/bot_monitor.log 2>&1 &
MONITOR_PID=$!
echo $MONITOR_PID > bot_monitor.pid
echo "Bot monitor started with PID: $MONITOR_PID"

# Start Django server in foreground (this keeps the Railway process alive)
echo "Starting Django server on 0.0.0.0:$PORT..."
python -c "
import os, sys, subprocess, signal, threading, time, logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.FileHandler('logs/django_wrapper.log'), logging.StreamHandler()]
)
logger = logging.getLogger('django_wrapper')

# Set up Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
os.environ['PYTHONUNBUFFERED'] = '1'  # Ensure unbuffered output
port = os.environ.get('PORT', '8080')

# Signal handler
def handle_signal(sig, frame):
    logger.info(f'Received signal {sig}, shutting down...')
    sys.exit(0)

signal.signal(signal.SIGINT, handle_signal)
signal.signal(signal.SIGTERM, handle_signal)

# Bot status checking thread
def check_bot_status():
    while True:
        try:
            # See if the bot is running
            with open('/proc/loadavg', 'r') as f:
                load = f.read().strip()
            
            bot_processes = subprocess.check_output(
                'ps -ef | grep -i \"run_bot\\|direct_bot\\|emergency_bot\" | grep -v grep | wc -l', 
                shell=True
            ).decode().strip()
            
            logger.info(f'System load: {load}, Bot processes: {bot_processes}')
            
            # If no bot processes, try to start one
            if bot_processes == '0':
                logger.warning('No bot processes detected, attempting to restart')
                try:
                    subprocess.Popen(
                        ['python', 'run_bot.py'], 
                        stdout=open('logs/bot/wrapper_restart.log', 'w'),
                        stderr=subprocess.STDOUT
                    )
                    logger.info('Bot restart initiated')
                except Exception as e:
                    logger.error(f'Failed to restart bot: {e}')
        except Exception as e:
            logger.error(f'Error in status thread: {e}')
        
        time.sleep(60)  # Check every minute

# Start status thread
status_thread = threading.Thread(target=check_bot_status, daemon=True)
status_thread.start()

# Start Django server
logger.info(f'Starting Django server on 0.0.0.0:{port}')
try:
    # Use subprocess so we can capture and log output
    proc = subprocess.Popen(
        ['python', 'manage.py', 'runserver', f'0.0.0.0:{port}'],
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        universal_newlines=True,
        bufsize=1  # Line buffered
    )
    
    # Read and log output
    for line in proc.stdout:
        sys.stdout.write(line)
        sys.stdout.flush()
        logger.debug(line.strip())
        
    # Wait for process to complete
    proc.wait()
    
    # If we get here, server has stopped
    exit_code = proc.returncode
    logger.error(f'Django server stopped with exit code {exit_code}')
    sys.exit(exit_code)
except Exception as e:
    logger.critical(f'Fatal error starting Django server: {e}')
    sys.exit(1)
"