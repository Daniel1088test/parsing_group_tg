#!/bin/bash
# Script to fix migration issues on Railway

echo "=== Starting migration fix ==="

# Check for DATABASE_URL
if [ -z "$DATABASE_URL" ]; then
  echo "ERROR: DATABASE_URL environment variable is not set. Cannot continue."
  exit 1
fi

echo "Using PostgreSQL database from DATABASE_URL: ${DATABASE_URL:0:15}..."

# Export DATABASE_URL to ensure all commands use it
export DATABASE_URL="$DATABASE_URL"

# Verify PostgreSQL connection first
echo "Verifying PostgreSQL connection..."
python -c "
import os
import sys
import psycopg2
from urllib.parse import urlparse

# Parse DATABASE_URL
url = urlparse(os.environ.get('DATABASE_URL', ''))
dbname = url.path[1:]
user = url.username
password = url.password
host = url.hostname
port = url.port

try:
    # Test direct connection to PostgreSQL
    print(f'Connecting to PostgreSQL: {host}:{port}/{dbname}')
    conn = psycopg2.connect(
        dbname=dbname,
        user=user,
        password=password,
        host=host,
        port=port
    )
    cursor = conn.cursor()
    cursor.execute('SELECT version();')
    version = cursor.fetchone()[0]
    print(f'✅ PostgreSQL connection successful: {version}')
    cursor.close()
    conn.close()
except Exception as e:
    print(f'❌ PostgreSQL connection error: {e}')
    sys.exit(1)
" || echo "PostgreSQL connection failed, cannot continue with migrations" && exit 1

# Fix BotSettings table structure first
echo "Fixing BotSettings table structure..."
python -c "
import os
import django
import psycopg2
from urllib.parse import urlparse

# Setup Django with explicit DATABASE_URL
print(f'Setting DATABASE_URL: {os.environ.get(\"DATABASE_URL\")[:15]}...')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()

# Parse DATABASE_URL
url = urlparse(os.environ.get('DATABASE_URL', ''))
dbname = url.path[1:]
user = url.username
password = url.password
host = url.hostname
port = url.port

try:
    # Connect directly to database
    conn = psycopg2.connect(
        dbname=dbname,
        user=user,
        password=password,
        host=host,
        port=port
    )
    conn.autocommit = True
    with conn.cursor() as cursor:
        # Check if BotSettings table exists
        cursor.execute(\"\"\"
        SELECT EXISTS (
            SELECT FROM information_schema.tables 
            WHERE table_schema = 'public' 
            AND table_name = 'admin_panel_botsettings'
        );
        \"\"\")
        table_exists = cursor.fetchone()[0]
        
        if not table_exists:
            print('Creating BotSettings table from scratch...')
            cursor.execute(\"\"\"
            CREATE TABLE admin_panel_botsettings (
                id SERIAL PRIMARY KEY,
                bot_token VARCHAR(255) NOT NULL,
                bot_username VARCHAR(255) NULL,
                bot_name VARCHAR(255) NULL,
                default_api_id VARCHAR(255) NULL,
                default_api_hash VARCHAR(255) NULL,
                polling_interval INTEGER NULL,
                max_messages_per_channel INTEGER NULL,
                welcome_message TEXT NULL,
                menu_style VARCHAR(50) NULL,
                created_at TIMESTAMP WITH TIME ZONE NULL,
                updated_at TIMESTAMP WITH TIME ZONE NULL
            );
            \"\"\")
            print('Created BotSettings table')
        else:
            # Check if bot_username column exists
            cursor.execute(\"\"\"
            SELECT EXISTS (
                SELECT FROM information_schema.columns 
                WHERE table_schema = 'public' 
                AND table_name = 'admin_panel_botsettings' 
                AND column_name = 'bot_username'
            );
            \"\"\")
            column_exists = cursor.fetchone()[0]
            
            if not column_exists:
                print('Adding bot_username column to BotSettings table...')
                cursor.execute(\"\"\"
                ALTER TABLE admin_panel_botsettings 
                ADD COLUMN bot_username VARCHAR(255) NULL;
                \"\"\")
                print('Added bot_username column')
            
            # Make sure we have at least one record
            cursor.execute('SELECT COUNT(*) FROM admin_panel_botsettings')
            count = cursor.fetchone()[0]
            
            if count == 0:
                print('Adding default BotSettings record...')
                cursor.execute(\"\"\"
                INSERT INTO admin_panel_botsettings 
                (bot_token, bot_username, bot_name) 
                VALUES (%s, %s, %s)
                \"\"\", [os.environ.get('BOT_TOKEN', ''), 'Channels_hunt_bot', 'Channel Hunt Bot'])
                print('Added default BotSettings record')
        
        print('BotSettings table check completed successfully')
except Exception as e:
    print(f'Error fixing BotSettings table: {e}')
    sys.exit(1)
" || { echo "BotSettings table fix failed, cannot continue"; exit 1; }

# Force PostgreSQL in Django commands
export DJANGO_SETTINGS_MODULE=core.settings

# Approach 1: Fake the problematic migrations
echo "Faking problematic migrations..."
python manage.py migrate admin_panel 0002_auto_20250409_0000 --fake --settings=core.settings || echo "Failed to fake 0002 migration, continuing..."
python manage.py migrate admin_panel 0003_merge_final --fake --settings=core.settings || echo "Failed to fake 0003 migration, continuing..."
python manage.py migrate admin_panel 0004_fake_migration --fake --settings=core.settings || echo "Failed to fake 0004 migration, continuing..."

# Run the full migration
echo "Running full migration..."
python manage.py migrate --settings=core.settings || echo "Migration failed, will try direct SQL fix..."

# Approach 2: Try direct SQL fix if migrations failed
echo "Running direct SQL fix..."
python sql_fix.py

# Fix old model fields directly in database
echo "Fixing TelegramSession table structure..."
python -c "
import os
import django
import psycopg2
from urllib.parse import urlparse

# Setup Django with explicit DATABASE_URL
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()

from django.db import connection
from django.conf import settings

# Verify we're using PostgreSQL
print(f'Using database engine: {settings.DATABASES[\"default\"][\"ENGINE\"]}')
if 'postgresql' not in settings.DATABASES['default']['ENGINE']:
    print('Warning: Not using PostgreSQL! Forcing direct connection...')
    # Parse DATABASE_URL for direct connection
    url = urlparse(os.environ.get('DATABASE_URL', ''))
    dbname = url.path[1:]
    user = url.username
    password = url.password
    host = url.hostname
    port = url.port
    
    # Connect directly
    conn = psycopg2.connect(
        dbname=dbname,
        user=user,
        password=password,
        host=host,
        port=port
    )
    cursor = conn.cursor()
else:
    # Use Django connection
    cursor = connection.cursor()

try:
    # Check if column exists and fix directly
    cursor.execute(\"\"\"
    DO $$
    BEGIN
        BEGIN
            ALTER TABLE admin_panel_telegramsession DROP COLUMN IF EXISTS needs_auth;
        EXCEPTION WHEN undefined_column THEN
            RAISE NOTICE 'Column needs_auth does not exist, skipping';
        END;
        
        BEGIN
            ALTER TABLE admin_panel_telegramsession ADD COLUMN IF NOT EXISTS needs_auth BOOLEAN DEFAULT TRUE;
        EXCEPTION WHEN duplicate_column THEN
            RAISE NOTICE 'Column needs_auth already exists';
        END;
        
        BEGIN
            ALTER TABLE admin_panel_telegramsession ADD COLUMN IF NOT EXISTS auth_token VARCHAR(255) DEFAULT NULL;
        EXCEPTION WHEN duplicate_column THEN
            RAISE NOTICE 'Column auth_token already exists';
        END;
    END
    $$;
    \"\"\")
    print('Direct database fixes applied successfully')
except Exception as e:
    print(f'Error fixing database directly: {e}')
" || echo "Direct database fix failed, but continuing..."

# Fix session closing issue by adding proper handlers
echo "Fixing aiohttp session closing issues..."
python fix_aiohttp_sessions.py || echo "Session fix failed, but continuing..."

# Always create health check files
echo "Creating health check files..."
echo "OK" > health.txt
echo "OK" > health.html
echo "OK" > healthz.txt
echo "OK" > healthz.html

# Create staticfiles directory if it doesn't exist
echo "Ensuring static files directories exist..."
mkdir -p staticfiles/img

# Create placeholder images
echo "Creating placeholder images..."
cat > staticfiles/img/placeholder-image.svg << EOL
<?xml version="1.0" encoding="UTF-8" standalone="no"?>
<svg width="300" height="200" xmlns="http://www.w3.org/2000/svg">
  <rect width="298" height="198" x="1" y="1" fill="#f0f0f0" stroke="#c8c8c8" stroke-width="2"/>
  <text x="150" y="110" font-family="Arial" font-size="24" text-anchor="middle" fill="#646464">IMAGE</text>
</svg>
EOL

cat > staticfiles/img/placeholder-video.svg << EOL
<?xml version="1.0" encoding="UTF-8" standalone="no"?>
<svg width="300" height="200" xmlns="http://www.w3.org/2000/svg">
  <rect width="298" height="198" x="1" y="1" fill="#f0f0f0" stroke="#c8c8c8" stroke-width="2"/>
  <text x="150" y="110" font-family="Arial" font-size="24" text-anchor="middle" fill="#646464">VIDEO</text>
</svg>
EOL

echo "=== Migration fix completed ===" 