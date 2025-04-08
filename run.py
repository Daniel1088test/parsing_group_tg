import os
import asyncio
import signal
import logging
import traceback
import argparse
import django
from multiprocessing import Queue
from datetime import datetime

# Configure logging for the entire project
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S',
    filename='app.log',
    filemode='a'
)
logger = logging.getLogger('run_script')

# Global variables to track the processes
processor_process = None
message_queue = None

# setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()

# Create necessary media directories
from django.conf import settings
os.makedirs(settings.MEDIA_ROOT, exist_ok=True)
os.makedirs(os.path.join(settings.MEDIA_ROOT, 'messages'), exist_ok=True)
logger.info(f"Ensured media directories exist: {settings.MEDIA_ROOT}/messages")

# Also create static img directory for placeholders
os.makedirs(os.path.join(settings.STATIC_ROOT, 'img'), exist_ok=True)

# Fix sessions and restore files if needed
from django.core.management import call_command
try:
    logger.info("Running fix_sessions command to ensure proper setup...")
    call_command('fix_sessions')
    logger.info("Completed fixing sessions and media files")
except Exception as e:
    logger.error(f"Error running fix_sessions command: {e}")
    logger.error(traceback.format_exc())

# Import the workers
from tg_bot.telethon_worker import telethon_worker_process