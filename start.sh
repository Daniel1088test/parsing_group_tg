#!/bin/bash

# Exit on any error
set -e

echo "Starting deployment script at $(date)"

# Set required environment variables
export PORT=${PORT:-8080}
export RAILWAY_PUBLIC_DOMAIN="${RAILWAY_PUBLIC_DOMAIN:-parsinggrouptg-production.up.railway.app}"
export PUBLIC_URL="https://$RAILWAY_PUBLIC_DOMAIN"
export WEB_SERVER_PORT=8000

echo "Using PORT: $PORT for Gunicorn (external)"
echo "Using WEB_SERVER_PORT: $WEB_SERVER_PORT for internal Django server"
echo "PUBLIC_URL: $PUBLIC_URL"

# Create necessary directories
mkdir -p staticfiles media data/messages data/sessions

# Prepare the environment
echo "Preparing environment..."
python manage.py collectstatic --noinput
python manage.py migrate --noinput

# Функція для зупинки всіх процесів Python
clean_processes() {
  echo "Cleaning up any existing processes..."
  # Шукаємо процеси за ключовими словами і зупиняємо їх
  ps -ef | grep -E "gunicorn|run.py|python.*run_bot_only.py|runserver" | grep -v grep | awk '{print $2}' | xargs -r kill -9 || echo "No processes to kill"
  
  # Очищаємо сесійні файли Telethon для уникнення конфліктів
  echo "Clearing Telethon session files..."
  find . -type f -name "*.session*" -delete 2>/dev/null || echo "No session files found"
  sleep 2
}

# Виконуємо очищення
clean_processes

# Start Gunicorn as a background process for external web access
echo "Starting Gunicorn web server (PORT=$PORT)..."
gunicorn core.wsgi:application --bind 0.0.0.0:$PORT --workers=1 --threads=4 --worker-class=gthread --worker-tmp-dir /dev/shm --log-level info &
GUNICORN_PID=$!
echo "Gunicorn started with PID: $GUNICORN_PID"

# Give Gunicorn time to fully start
echo "Waiting for web server to initialize..."
sleep 5

# Create a modified run.py that doesn't kill other processes
cat > run_bot_only.py << 'EOF'
import sys
import os
import signal
import asyncio
import logging
import multiprocessing
import queue
import traceback
from datetime import datetime

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('bot.log', encoding='utf-8')
    ]
)
logger = logging.getLogger('bot_runner')

# Global variables to track processes
telethon_process = None
processor_process = None
message_queue = None

async def run_bot():
    """Start Telegram bot without starting Django server"""
    logger.info("Starting Telegram bot...")
    try:
        # Use existing Django setup
        import django
        os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
        django.setup()
        
        from tg_bot.bot import main
        await main()
    except Exception as e:
        logger.error(f"Error starting bot: {e}")
        logger.error(f"Traceback: {traceback.format_exc()}")
        raise

def run_telethon_parser(message_queue):
    """Start Telethon parser"""
    logger.info("Starting Telethon parser...")
    try:
        # Use existing Django setup
        import django
        os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
        django.setup()
        
        # Import configuration
        from tg_bot.config import DATA_FOLDER
        
        # Create session directory if it doesn't exist
        session_dir = os.path.join(DATA_FOLDER, 'sessions')
        os.makedirs(session_dir, exist_ok=True)
        
        # Check for session files in multiple locations
        session_paths = [
            'telethon_user_session.session',
            'telethon_session.session',
            os.path.join(session_dir, 'telethon_user_session.session'),
            os.path.join(session_dir, 'telethon_session.session')
        ]
        
        session_exists = any(os.path.exists(path) for path in session_paths)
        
        if not session_exists:
            logger.warning("No Telethon session file found. Please authorize using the Telegram bot.")
            logger.warning("IMPORTANT: You must use a regular user account, NOT a bot!")
            logger.warning("Telethon parser will not be started.")
            return
            
        from tg_bot.telethon_worker import telethon_worker_process
        telethon_worker_process(message_queue)
    except Exception as e:
        logger.error(f"Error starting Telethon parser: {e}")
        logger.error(f"Traceback: {traceback.format_exc()}")

def message_processor(message_queue):
    """Process messages from Telethon parser"""
    logger.info("Starting message processor...")
    try:
        # Use existing Django setup
        import django
        os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
        django.setup()
        
        while True:
            try:
                # Get message from queue (if queue is empty, wait)
                message = message_queue.get(block=True, timeout=1)
                logger.debug(f"Received message from queue: {message.get('message_info', {}).get('message_id')}")
            except queue.Empty:
                continue
            except Exception as e:
                logger.error(f"Error processing message: {e}")
    except Exception as e:
        logger.error(f"Fatal error in message processor: {e}")
        logger.error(f"Traceback: {traceback.format_exc()}")

async def run_services():
    """Main function to run all services"""
    global telethon_process, processor_process, message_queue
    
    start_time = datetime.now()
    logger.info(f"====== Starting bot services {start_time.strftime('%Y-%m-%d %H:%M:%S')} ======")
    
    # Create a queue for inter-process communication
    message_queue = multiprocessing.Queue()
    
    try:
        # Don't mess with any other Python processes - that's the key fix
        logger.info("Using existing web server...")
        
        # Start message processor
        processor_process = multiprocessing.Process(
            target=message_processor,
            args=(message_queue,)
        )
        processor_process.daemon = True
        processor_process.start()
        logger.info(f"Message processor process started (PID: {processor_process.pid})")
        
        # Start Telethon parser
        telethon_process = multiprocessing.Process(
            target=run_telethon_parser,
            args=(message_queue,)
        )
        telethon_process.daemon = True
        telethon_process.start()
        logger.info(f"Telethon parser process started (PID: {telethon_process.pid})")
        
        # Wait for processes to initialize
        await asyncio.sleep(3)
        
        # Start bot
        await run_bot()
        
    except KeyboardInterrupt:
        logger.info("\nReceived termination signal (KeyboardInterrupt)")
    except Exception as e:
        logger.error(f"Critical error during service execution: {e}")
        logger.error(f"Traceback: {traceback.format_exc()}")
    finally:
        # Shut down our processes
        await shutdown_services()
        
        # Log runtime information
        end_time = datetime.now()
        runtime = end_time - start_time
        logger.info(f"Bot services stopped. Runtime: {runtime}")
        logger.info("====== End ======")

async def shutdown_services():
    """Shutdown all services cleanly"""
    global telethon_process, processor_process
    
    logger.info("Stopping bot services...")
    
    # Stop Telethon parser
    if telethon_process and telethon_process.is_alive():
        logger.info("Stopping Telethon parser...")
        telethon_process.terminate()
        telethon_process.join(timeout=5)
        if telethon_process.is_alive():
            logger.warning("Telethon parser did not terminate gracefully, forcing...")
            os.kill(telethon_process.pid, signal.SIGKILL)
    
    # Stop message processor
    if processor_process and processor_process.is_alive():
        logger.info("Stopping message processor...")
        processor_process.terminate()
        processor_process.join(timeout=5)
        if processor_process.is_alive():
            logger.warning("Message processor did not terminate gracefully, forcing...")
            os.kill(processor_process.pid, signal.SIGKILL)

if __name__ == "__main__":
    logger.info("Starting Bot Process")
    
    try:
        asyncio.run(run_services())
    except Exception as e:
        logger.error(f"Fatal error in main process: {e}")
        logger.error(f"Traceback: {traceback.format_exc()}")
        sys.exit(1)
EOF

# Start the modified bot script that won't kill gunicorn
echo "Starting bot process without killing other processes..."
python run_bot_only.py &
BOT_PID=$!
echo "Bot started with PID: $BOT_PID"

# Monitor main web process
echo "All processes started. Monitoring..."
wait $GUNICORN_PID 