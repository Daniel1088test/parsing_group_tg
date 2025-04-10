import logging
import subprocess
import sys
import os
import time
import signal
from django.core.management.base import BaseCommand

logger = logging.getLogger(__name__)

class Command(BaseCommand):
    help = 'Start the Django server and Telegram bot together'

    def add_arguments(self, parser):
        parser.add_argument(
            '--port',
            type=int,
            default=8000,
            help='Port to run the server on',
        )
        parser.add_argument(
            '--host',
            type=str,
            default='0.0.0.0',
            help='Host to bind the server to',
        )
        parser.add_argument(
            '--no-bot',
            action='store_true',
            help='Do not start the bot, only the server',
        )

    def handle(self, *args, **options):
        port = options['port']
        host = options['host']
        no_bot = options['no_bot']
        
        # Fix database schema first
        self.stdout.write("Fixing database schema...")
        from django.core.management import call_command
        call_command('fix_db_schema')
        
        # Start the bot in a separate process if not disabled
        bot_process = None
        if not no_bot:
            try:
                self.stdout.write("Starting bot process...")
                bot_process = subprocess.Popen([sys.executable, 'run.py'], 
                                            stdout=subprocess.PIPE,
                                            stderr=subprocess.STDOUT)
                self.stdout.write(self.style.SUCCESS(f"Bot started with PID: {bot_process.pid}"))
            except Exception as e:
                self.stdout.write(self.style.ERROR(f"Failed to start bot: {e}"))
                bot_process = None
        
        # Start the Django server
        self.stdout.write(f"Starting Django server on {host}:{port}...")
        
        # Using subprocess.call would wait until the server is stopped
        # Instead, we record it as the main process and let it run
        try:
            self.stdout.write(self.style.SUCCESS("Django and bot processes started"))
            self.stdout.write("Press Ctrl+C to stop all processes")
            
            # Wait for keyboard interrupt
            while True:
                time.sleep(1)
                
                # Check if bot is still running
                if bot_process and bot_process.poll() is not None:
                    self.stdout.write(self.style.WARNING("Bot process has terminated. Restarting..."))
                    bot_process = subprocess.Popen([sys.executable, 'run.py'], 
                                                stdout=subprocess.PIPE,
                                                stderr=subprocess.STDOUT)
                    self.stdout.write(self.style.SUCCESS(f"Bot restarted with PID: {bot_process.pid}"))
                
        except KeyboardInterrupt:
            self.stdout.write("Stopping all processes...")
            if bot_process:
                bot_process.terminate()
                self.stdout.write("Bot process terminated")
                
        self.stdout.write(self.style.SUCCESS("All processes stopped")) 