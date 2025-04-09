#!/bin/bash
# Comprehensive startup script for Railway deployment

echo "===== STARTING ALL SERVICES ====="

# 1. Create health check files immediately
echo "Creating health check files..."
mkdir -p staticfiles
echo "OK" > health.txt
echo "<html><body>OK</body></html>" > health.html
echo "OK" > healthz.txt
echo "<html><body>OK</body></html>" > healthz.html

# 2. Start health check server in background
echo "Starting health check server..."
# Set health check port to avoid conflict with Django
export HEALTH_PORT=3000
nohup python railway_health.py > logs/health_server.log 2>&1 &
HEALTH_PID=$!
echo $HEALTH_PID > health_server.pid

# 3. Create necessary directories
echo "Creating required directories..."
mkdir -p staticfiles/img
mkdir -p media/messages
mkdir -p logs/bot
mkdir -p data/sessions

# 4. Verify database connection
echo "Verifying database connection..."
if [ -z "$DATABASE_URL" ]; then
  echo "⚠️ DATABASE_URL not set, using SQLite fallback"
else
  echo "Using PostgreSQL from DATABASE_URL: ${DATABASE_URL:0:15}..."
  
  # Test connection
  python -c "
import os, sys, psycopg2
from urllib.parse import urlparse
try:
    url = urlparse(os.environ.get('DATABASE_URL', ''))
    dbname = url.path[1:]
    user = url.username
    password = url.password
    host = url.hostname
    port = url.port
    print(f'Connecting to PostgreSQL: {host}:{port}/{dbname}')
    conn = psycopg2.connect(dbname=dbname, user=user, password=password, host=host, port=port)
    cursor = conn.cursor()
    cursor.execute('SELECT version();')
    version = cursor.fetchone()[0]
    print(f'✅ PostgreSQL connection successful: {version}')
    cursor.close()
    conn.close()
except Exception as e:
    print(f'❌ PostgreSQL connection error: {e}')
    print('Will use fallback database configuration')
    sys.exit(1)
"
  if [ $? -ne 0 ]; then
    echo "⚠️ PostgreSQL connection failed, check logs"
  fi
fi

# 5. Fix database issues
echo "Running database fixes..."
python -c "
import os
import django
import sys

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()

# Fix database issues
from django.db import connection
from django.conf import settings

print(f'Using database: {settings.DATABASES[\"default\"][\"ENGINE\"]}')

# Add missing columns
try:
    with connection.cursor() as cursor:
        # BotSettings fixes - fixed syntax error
        cursor.execute('''
        DO $$
        BEGIN
            BEGIN
                ALTER TABLE IF EXISTS admin_panel_botsettings 
                ADD COLUMN IF NOT EXISTS bot_username VARCHAR(255);
            EXCEPTION WHEN duplicate_column THEN
                RAISE NOTICE 'Column bot_username already exists';
            END;
            
            BEGIN
                ALTER TABLE IF EXISTS admin_panel_telegramsession 
                ADD COLUMN IF NOT EXISTS needs_auth BOOLEAN DEFAULT TRUE;
            EXCEPTION WHEN duplicate_column THEN
                RAISE NOTICE 'Column needs_auth already exists';
            END;
            
            BEGIN
                ALTER TABLE IF EXISTS admin_panel_telegramsession 
                ADD COLUMN IF NOT EXISTS auth_token VARCHAR(255);
            EXCEPTION WHEN duplicate_column THEN
                RAISE NOTICE 'Column auth_token already exists';
            END;
        END;
        $$;
        ''')
        print('✅ Database structure fixed')
        
        # Check for BotSettings entry
        if 'admin_panel_botsettings' in connection.introspection.table_names():
            cursor.execute('SELECT COUNT(*) FROM admin_panel_botsettings')
            count = cursor.fetchone()[0]
            if count == 0:
                print('Adding default BotSettings record')
                cursor.execute('''
                INSERT INTO admin_panel_botsettings 
                (bot_token, bot_username, bot_name, created_at, updated_at) 
                VALUES (%s, %s, %s, NOW(), NOW())
                ''', [os.environ.get('BOT_TOKEN', ''), 'Channels_hunt_bot', 'Channel Hunt Bot'])
                print('✅ Added default BotSettings')
except Exception as e:
    print(f'⚠️ Database fix error: {e}')
    print('Will continue with startup')
"

# 6. Run migrations
echo "Running migrations..."
python manage.py migrate --noinput || echo "⚠️ Migration issues, but continuing"

# 7. Collect static files
echo "Collecting static files..."
python manage.py collectstatic --noinput || echo "⚠️ Static files issue, but continuing"

# 8. Fix aiohttp session closing issues
echo "Fixing aiohttp sessions..."
python fix_aiohttp_sessions.py || echo "⚠️ Session fix failed, but continuing"

# 9. Start Telegram bot in background
echo "Starting Telegram bot..."
mkdir -p logs/bot
chmod +x direct_bot_runner.py

# Try to start bot with retries
BOT_MAX_RETRIES=3
BOT_RETRY_COUNT=0
BOT_STARTED=false

while [ $BOT_RETRY_COUNT -lt $BOT_MAX_RETRIES ] && [ "$BOT_STARTED" = false ]; do
  nohup python direct_bot_runner.py > logs/bot/bot.log 2>&1 &
  BOT_PID=$!
  echo $BOT_PID > bot.pid
  
  # Wait a moment to see if it crashes immediately
  sleep 3
  
  # Check if process is still running
  if ps -p $BOT_PID > /dev/null; then
    echo "Bot started successfully with PID: $BOT_PID"
    BOT_STARTED=true
    
    # Check if the log contains successful connection
    if grep -q "Bot connection verified" logs/bot/bot.log; then
      echo "✅ Bot successfully connected to Telegram API"
    fi
  else
    BOT_RETRY_COUNT=$((BOT_RETRY_COUNT + 1))
    echo "Bot failed to start (attempt $BOT_RETRY_COUNT/$BOT_MAX_RETRIES)"
    sleep 3
  fi
done

if [ "$BOT_STARTED" = false ]; then
  echo "⚠️ Failed to start bot after $BOT_MAX_RETRIES attempts"
  echo "Will rely on process monitor to retry later"
fi

# 10. Start parser in background if the file exists
if [ -f "run_parser.py" ]; then
  echo "Starting parser..."
  mkdir -p logs/parser
  
  # Try to start parser with retries
  PARSER_MAX_RETRIES=3
  PARSER_RETRY_COUNT=0
  PARSER_STARTED=false
  
  while [ $PARSER_RETRY_COUNT -lt $PARSER_MAX_RETRIES ] && [ "$PARSER_STARTED" = false ]; do
    nohup python run_parser.py > logs/parser/parser.log 2>&1 &
    PARSER_PID=$!
    echo $PARSER_PID > parser.pid
    
    # Wait a moment to see if it crashes immediately
    sleep 2
    
    # Check if process is still running
    if ps -p $PARSER_PID > /dev/null; then
      echo "Parser started successfully with PID: $PARSER_PID"
      PARSER_STARTED=true
    else
      PARSER_RETRY_COUNT=$((PARSER_RETRY_COUNT + 1))
      echo "Parser failed to start (attempt $PARSER_RETRY_COUNT/$PARSER_MAX_RETRIES)"
      sleep 3
    fi
  done
  
  if [ "$PARSER_STARTED" = false ]; then
    echo "⚠️ Failed to start parser after $PARSER_MAX_RETRIES attempts"
    echo "Will rely on process monitor to retry later"
  fi
fi

# 11. Monitor process
echo "Starting process monitor..."
nohup python -c "
import os, sys, time, signal, subprocess

def check_process(pid_file, name):
    if not os.path.exists(pid_file):
        return False
    
    try:
        with open(pid_file, 'r') as f:
            pid = int(f.read().strip())
        
        # Check if process is running
        os.kill(pid, 0)
        return True
    except (ProcessLookupError, ValueError, FileNotFoundError):
        print(f'{name} process is not running, restarting...')
        return False

def restart_process(script, log_file, pid_file, name):
    try:
        proc = subprocess.Popen(['python', script], 
                                stdout=open(log_file, 'a'),
                                stderr=subprocess.STDOUT)
        with open(pid_file, 'w') as f:
            f.write(str(proc.pid))
        print(f'Restarted {name} with PID: {proc.pid}')
        return True
    except Exception as e:
        print(f'Failed to restart {name}: {e}')
        return False

# Monitor loop
print('Starting process monitor...')
while True:
    # Check bot
    if not check_process('bot.pid', 'Bot'):
        restart_process('direct_bot_runner.py', 'logs/bot/bot.log', 'bot.pid', 'Bot')
    
    # Check parser if exists
    if os.path.exists('run_parser.py') and not check_process('parser.pid', 'Parser'):
        restart_process('run_parser.py', 'logs/parser/parser.log', 'parser.pid', 'Parser')
    
    # Check health server
    if not check_process('health_server.pid', 'Health Server'):
        restart_process('railway_health.py', 'logs/health_server.log', 'health_server.pid', 'Health Server')
    
    # Sleep before next check
    time.sleep(30)
" > logs/monitor.log 2>&1 &
MONITOR_PID=$!
echo $MONITOR_PID > monitor.pid
echo "Process monitor started with PID: $MONITOR_PID"

# 12. Start Django application (main process)
echo "Starting Django application..."
PORT=${PORT:-8080}
echo "Using port: $PORT"

# Check if port is in use and kill the process using it
echo "Checking if port $PORT is in use..."
python -c "
import socket
import os
import signal
import subprocess
import time

def check_port_in_use(port):
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        return s.connect_ex(('localhost', port)) == 0

def find_process_using_port(port):
    try:
        # For Linux/Unix
        output = subprocess.check_output(['lsof', '-i', f':{port}'], text=True)
        lines = output.strip().split('\\n')
        if len(lines) > 1:  # Skip header
            # Extract PID from the second column
            return int(lines[1].split()[1])
    except:
        try:
            # Alternative approach
            output = subprocess.check_output(['fuser', f'{port}/tcp'], text=True)
            return int(output.strip().split()[0])
        except:
            return None
    return None

# Check if port is in use
port = int(os.environ.get('PORT', 8080))
if check_port_in_use(port):
    print(f'Port {port} is in use')
    pid = find_process_using_port(port)
    if pid:
        print(f'Killing process {pid} using port {port}')
        try:
            os.kill(pid, signal.SIGTERM)
            # Wait a moment for the process to terminate
            time.sleep(2)
        except:
            print(f'Failed to kill process {pid}')
    else:
        print(f'Could not find process using port {port}')

    # Verify port is now available
    if check_port_in_use(port):
        print(f'Port {port} is still in use. Will try to continue anyway.')
    else:
        print(f'Port {port} is now available')
else:
    print(f'Port {port} is available')
" || echo "Port check failed, continuing anyway"

# Start Django
exec gunicorn core.wsgi:application --bind 0.0.0.0:$PORT --log-file - 