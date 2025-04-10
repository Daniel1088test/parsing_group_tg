import asyncio
import os
import sys
import time
import signal
import subprocess
import logging
from django.core.management.base import BaseCommand
from django.conf import settings

logger = logging.getLogger('bot_monitor')

class Command(BaseCommand):
    help = 'Monitor and ensure the Telegram bot is running'
    
    def add_arguments(self, parser):
        parser.add_argument(
            '--daemon',
            action='store_true',
            help='Run in daemon mode, continuously monitoring the bot',
        )
    
    def handle(self, *args, **options):
        daemon_mode = options.get('daemon', False)
        
        if daemon_mode:
            self.stdout.write(self.style.SUCCESS('Starting bot monitor in daemon mode...'))
            self.monitor_bot_continuously()
        else:
            self.stdout.write(self.style.SUCCESS('Checking bot status and ensuring it is running...'))
            self.check_and_start_bot()
    
    def check_and_start_bot(self):
        """Check if the bot is running and start it if needed"""
        self.stdout.write('Checking for running bot processes...')
        
        # Check for any existing bot processes
        bot_running = False
        try:
            # Different ways to check for the bot process
            bot_processes = self.run_command("ps -ef | grep -i 'python.*bot.py\\|run_bot.py' | grep -v grep")
            
            if bot_processes.strip():
                self.stdout.write(self.style.SUCCESS('✅ Bot process is already running:'))
                self.stdout.write(bot_processes)
                bot_running = True
            else:
                self.stdout.write(self.style.WARNING('⚠️ No bot process detected'))
        except Exception as e:
            self.stderr.write(self.style.ERROR(f'Error checking bot process: {e}'))
        
        # If bot is not running, start it
        if not bot_running:
            self.stdout.write('Starting the bot...')
            try:
                # Create log directory if it doesn't exist
                os.makedirs('logs/bot', exist_ok=True)
                
                # Start the bot in a new process
                bot_proc = subprocess.Popen(
                    [sys.executable, 'run_bot.py'],
                    stdout=open('logs/bot/monitor_started_bot.log', 'w'),
                    stderr=subprocess.STDOUT,
                    env=os.environ.copy()
                )
                
                # Save PID to file
                with open('monitor_bot.pid', 'w') as f:
                    f.write(str(bot_proc.pid))
                
                self.stdout.write(self.style.SUCCESS(f'✅ Bot started successfully with PID {bot_proc.pid}'))
                
                # Wait a moment to see if it immediately crashes
                time.sleep(5)
                if bot_proc.poll() is None:
                    self.stdout.write(self.style.SUCCESS('✅ Bot process is still running after 5 seconds'))
                else:
                    self.stderr.write(self.style.ERROR(f'❌ Bot process exited immediately with code {bot_proc.poll()}'))
                    self.stdout.write('Check logs/bot/monitor_started_bot.log for details')
            except Exception as e:
                self.stderr.write(self.style.ERROR(f'Error starting bot: {e}'))
    
    def monitor_bot_continuously(self):
        """Run in a loop, continuously monitoring the bot"""
        self.stdout.write('Starting continuous bot monitoring...')
        
        # Register signal handlers
        def handle_signal(sig, frame):
            self.stdout.write(self.style.WARNING('Received termination signal, stopping monitor...'))
            sys.exit(0)
        
        signal.signal(signal.SIGINT, handle_signal)
        signal.signal(signal.SIGTERM, handle_signal)
        
        restart_count = 0
        max_restarts = 10
        restart_interval = 60  # seconds
        
        while True:
            try:
                # Check and start the bot if needed
                self.check_and_start_bot()
                
                # Log that we're still monitoring
                self.stdout.write(f'Bot monitor is active. Restarts so far: {restart_count}')
                
                # Sleep before checking again
                time.sleep(restart_interval)
                
                # Increase the interval over time to avoid rapid restarts
                if restart_count > 3:
                    # After 3 restarts, check less frequently
                    restart_interval = 300  # 5 minutes
                elif restart_count > 5:
                    # After 5 restarts, check even less frequently
                    restart_interval = 600  # 10 minutes
                
                # Check if we've hit the restart limit
                if restart_count >= max_restarts:
                    self.stderr.write(self.style.ERROR(
                        f'Reached maximum restart limit ({max_restarts}). '
                        'Please check the logs and fix the underlying issue.'
                    ))
                    break
            except Exception as e:
                self.stderr.write(self.style.ERROR(f'Error in monitor loop: {e}'))
                time.sleep(60)  # Wait a minute before trying again after an error
    
    def run_command(self, command):
        """Run a shell command and return the output"""
        process = subprocess.Popen(
            command,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            shell=True,
            universal_newlines=True
        )
        stdout, stderr = process.communicate()
        
        if process.returncode != 0 and stderr:
            raise Exception(f"Command failed: {stderr}")
        
        return stdout 