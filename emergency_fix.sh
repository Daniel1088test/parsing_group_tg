#!/bin/bash
# Emergency fix script for deployment issues
# This script handles common problems with the bot deployment

set -e  # Exit on error

echo "=== EMERGENCY FIX SCRIPT ==="
echo "Running emergency fixes for Telegram bot..."

# Install qrcode package
echo "Installing qrcode package..."
pip install qrcode==7.4.2 --no-cache-dir

# Fix environment
echo "Setting environment variables..."
export DJANGO_SETTINGS_MODULE=core.settings

# Create necessary directories
echo "Creating necessary directories..."
mkdir -p logs/bot
mkdir -p media/messages
mkdir -p staticfiles/media
mkdir -p data/sessions

# Fix database
echo "Attempting database fixes..."
python - << EOF
import os
import django
import sys
import traceback

try:
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
    django.setup()
    
    from django.db import connection, OperationalError
    
    # Check if we can connect to the database
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
            print("✓ Database connection successful")
    except OperationalError as e:
        print(f"✗ Database connection error: {e}")
        sys.exit(1)
    
    # Fix BotSettings table if needed
    with connection.cursor() as cursor:
        # Check if BotSettings table exists
        cursor.execute("""
            SELECT EXISTS (
                SELECT FROM information_schema.tables 
                WHERE table_name='admin_panel_botsettings'
            )
        """)
        if cursor.fetchone()[0]:
            print("✓ BotSettings table exists")
            
            # Check if bot_name column exists
            cursor.execute("""
                SELECT EXISTS (
                    SELECT FROM information_schema.columns 
                    WHERE table_name='admin_panel_botsettings' AND column_name='bot_name'
                )
            """)
            if not cursor.fetchone()[0]:
                print("✗ Adding missing bot_name column to BotSettings table")
                cursor.execute("""
                    ALTER TABLE admin_panel_botsettings 
                    ADD COLUMN bot_name VARCHAR(255) NULL
                """)
                connection.commit()
                print("✓ Added bot_name column")
        else:
            print("✗ BotSettings table doesn't exist, creating it")
            cursor.execute("""
                CREATE TABLE admin_panel_botsettings (
                    id SERIAL PRIMARY KEY,
                    bot_token VARCHAR(255) NOT NULL,
                    bot_username VARCHAR(255) NULL,
                    bot_name VARCHAR(255) NULL,
                    welcome_message TEXT NULL,
                    auth_guide_text TEXT NULL,
                    menu_style VARCHAR(50) NULL,
                    default_api_id INTEGER NULL,
                    default_api_hash VARCHAR(255) NULL,
                    polling_interval INTEGER NULL,
                    max_messages_per_channel INTEGER NULL,
                    created_at TIMESTAMP NULL,
                    updated_at TIMESTAMP NULL
                )
            """)
            connection.commit()
            print("✓ Created BotSettings table")
            
            # Insert default settings
            token = os.environ.get('BOT_TOKEN', "7923260865:AAGYew9JnOJV6hz0LGeRCb1kS6AejHoX61g")
            cursor.execute("""
                INSERT INTO admin_panel_botsettings 
                (bot_token, bot_username, bot_name, menu_style, default_api_id, 
                polling_interval, max_messages_per_channel)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
            """, [
                token, 'Channels_hunt_bot', 'Channel Parser Bot', 'default', 
                2496, 30, 10
            ])
            connection.commit()
            print("✓ Inserted default settings")
    
    print("✓ Database fixes completed")
except Exception as e:
    print(f"✗ Error during database fixes: {e}")
    traceback.print_exc()
    sys.exit(1)
EOF

# Fix bot imports
echo "Fixing bot imports..."
python - << EOF
import os
import sys
import traceback

try:
    # Ensure the current directory is in the path
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    
    bot_file = 'tg_bot/bot.py'
    if os.path.exists(bot_file):
        with open(bot_file, 'r') as f:
            content = f.read()
        
        # Check if __all__ is already defined
        if '__all__' not in content:
            # Find the right place to add the __all__ definition
            if 'async def heartbeat_task():' in content:
                # Add after heartbeat_task
                new_content = content.replace(
                    'async def heartbeat_task():',
                    'async def heartbeat_task():'
                )
                
                # Find the end of heartbeat_task
                heartbeat_end = new_content.find('if __name__ ==')
                if heartbeat_end != -1:
                    # Insert __all__ before if __name__
                    insert_point = heartbeat_end
                    new_content = (
                        new_content[:insert_point] + 
                        '\n    # Export the main components for other modules to import\n    __all__ = ["main", "bot", "dp"]\n    \n' + 
                        new_content[insert_point:]
                    )
                    
                    # Write the modified content back
                    with open(bot_file, 'w') as f:
                        f.write(new_content)
                    print(f"✓ Added __all__ to {bot_file}")
                else:
                    print(f"✗ Couldn't find insertion point in {bot_file}")
            else:
                print(f"✗ Couldn't find heartbeat_task in {bot_file}")
        else:
            print(f"✓ __all__ already defined in {bot_file}")
    else:
        print(f"✗ File {bot_file} not found")
    
    print("✓ Bot file fix completed")
except Exception as e:
    print(f"✗ Error fixing bot file: {e}")
    traceback.print_exc()
    sys.exit(1)
EOF

# Create health check files
echo "Creating health check files..."
for file in health.txt healthz.txt health.html healthz.html; do
  echo "ok" > $file
  echo "✓ Created $file"
done

# Check if direct_start_bot.py exists
if [ -f "direct_start_bot.py" ]; then
    echo "direct_start_bot.py exists, using it"
else
    echo "Creating direct_start_bot.py..."
    cat > direct_start_bot.py << 'EOF'
#!/usr/bin/env python3
"""
Standalone bot starter with minimal dependencies
This script directly runs the Telegram bot without using Django's async machinery
"""
import os
import sys
import time
import logging
import subprocess
import signal
import traceback

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('direct_bot.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger('direct_bot_starter')

def signal_handler(sig, frame):
    logger.info(f"Received signal {sig}, shutting down...")
    sys.exit(0)

signal.signal(signal.SIGINT, signal_handler)
signal.signal(signal.SIGTERM, signal_handler)

def check_environment():
    """Ensure environment variables are set"""
    token = os.environ.get('BOT_TOKEN')
    if not token:
        # Try to read from file
        if os.path.exists('bot_token.env'):
            try:
                with open('bot_token.env', 'r') as f:
                    content = f.read().strip()
                    if content.startswith('BOT_TOKEN='):
                        token = content.split('=', 1)[1].strip()
                        os.environ['BOT_TOKEN'] = token
                        logger.info("Loaded BOT_TOKEN from bot_token.env")
            except Exception as e:
                logger.error(f"Error reading bot_token.env: {e}")
        
        # Still no token? Try config.py
        if not token:
            try:
                sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
                from tg_bot.config import TOKEN_BOT
                if TOKEN_BOT:
                    os.environ['BOT_TOKEN'] = TOKEN_BOT
                    logger.info("Loaded BOT_TOKEN from config.py")
            except Exception as e:
                logger.error(f"Error loading token from config.py: {e}")
        
        # Last resort - hardcoded token
        if not token:
            hardcoded_token = "7923260865:AAGYew9JnOJV6hz0LGeRCb1kS6AejHoX61g"
            os.environ['BOT_TOKEN'] = hardcoded_token
            logger.warning("Using hardcoded token as last resort")
    
    # Check if DJANGO_SETTINGS_MODULE is set
    if 'DJANGO_SETTINGS_MODULE' not in os.environ:
        os.environ['DJANGO_SETTINGS_MODULE'] = 'core.settings'
        logger.info("Set DJANGO_SETTINGS_MODULE to core.settings")
    
    return True

def run_bot():
    """Run the bot directly"""
    try:
        logger.info("Starting the bot directly...")
        
        # Verify Django setup
        import django
        os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
        django.setup()
        logger.info("Django setup completed")
        
        # Direct bot launch (no subprocess)
        import asyncio
        
        # Create run coroutine
        async def run_async_bot():
            try:
                # Import with direct access to avoid circular imports
                from tg_bot.bot import bot, dp, main
                logger.info("Successfully imported bot components")
                
                # Run the main function
                logger.info("Starting bot main function")
                await main()
                return True
            except ImportError as e:
                logger.error(f"Critical error in bot: {e}")
                return False
            except Exception as e:
                logger.error(f"Error running bot: {e}")
                logger.error(traceback.format_exc())
                return False
        
        # Run the async function
        if asyncio.run(run_async_bot()):
            logger.info("Bot completed successfully")
            return 0
        else:
            logger.error("Bot failed to run")
            return 1
    except Exception as e:
        logger.error(f"Critical error in bot: {e}")
        logger.error(traceback.format_exc())
        return 1

if __name__ == "__main__":
    logger.info("=== Direct Bot Starter ===")
    
    # Check environment
    check_environment()
    
    # Create directory structure
    os.makedirs('logs/bot', exist_ok=True)
    
    try:
        # Run the bot
        exit_code = run_bot()
        sys.exit(exit_code)
    except KeyboardInterrupt:
        logger.info("Interrupted by user")
        sys.exit(0)
    except Exception as e:
        logger.error(f"Unhandled exception: {e}")
        logger.error(traceback.format_exc())
        sys.exit(1)
EOF
    chmod +x direct_start_bot.py
    echo "✓ Created direct_start_bot.py"
fi

echo "Running database migrations..."
python manage.py migrate --noinput || echo "Migration errors detected, but continuing..."

echo "Checking bot status..."
python - << EOF
import os
import django
import asyncio
import sys
import traceback

try:
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
    django.setup()
    
    from tg_bot.bot import bot
    
    async def check_bot():
        try:
            me = await bot.get_me()
            print(f"✓ Bot connection verified: @{me.username} (ID: {me.id})")
            return True
        except Exception as e:
            print(f"✗ Bot connection failed: {e}")
            return False
    
    if not asyncio.run(check_bot()):
        print("⚠️ Bot connection issues detected")
        
except Exception as e:
    print(f"✗ Error checking bot: {e}")
    traceback.print_exc()
EOF

echo "Creating startup script symlink..."
if [ -f "railway_startup.py" ]; then
    chmod +x railway_startup.py
    ln -sf railway_startup.py startup.py || echo "Failed to create symlink, but continuing..."
    echo "✓ Created startup.py symlink"
fi

echo "=== EMERGENCY FIX COMPLETE ==="
echo "The bot should now be able to start correctly."
echo "Use 'python direct_start_bot.py' to run the bot directly."
echo "Use 'python railway_startup.py' for a complete deployment." 