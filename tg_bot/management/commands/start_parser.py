import os
import subprocess
from django.core.management.base import BaseCommand
import logging

logger = logging.getLogger(__name__)

class Command(BaseCommand):
    help = 'Start the Telegram parser in background mode'

    def add_arguments(self, parser):
        parser.add_argument(
            '--daemon',
            action='store_true',
            help='Run in daemon mode (detached from the terminal)',
        )

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS('Starting Telegram parser...'))
        
        daemon_mode = options.get('daemon', False)
        
        # Get the script path
        parser_script = os.path.join(os.getcwd(), 'run_parser.py')
        
        if not os.path.exists(parser_script):
            self.stdout.write(self.style.ERROR(f'Parser script not found at {parser_script}'))
            return
        
        try:
            if daemon_mode:
                # Start in background with nohup
                process = subprocess.Popen(
                    ['nohup', 'python', parser_script, '&'],
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    preexec_fn=os.setpgrp
                )
                self.stdout.write(self.style.SUCCESS(f'Parser started in daemon mode with PID: {process.pid}'))
            else:
                # Start in foreground
                self.stdout.write(self.style.SUCCESS('Starting parser in foreground mode. Press Ctrl+C to stop.'))
                subprocess.run(['python', parser_script], check=True)
        except subprocess.SubprocessError as e:
            self.stdout.write(self.style.ERROR(f'Error starting parser: {e}'))
        except KeyboardInterrupt:
            self.stdout.write(self.style.SUCCESS('Parser stopped by user'))