import multiprocessing
import queue
import time
import os
import sys
from django.core.management.base import BaseCommand
import logging
from django.utils import timezone
from admin_panel.models import Channel, Message, TelegramSession
import traceback

# Configuration of logging
logger = logging.getLogger('django')

def process_message(message_data):
    """Process message from queue in main thread with Django ORM access"""
    try:
        message_info = message_data.get('message_info', {})
        message_id = message_info.get('message_id')
        channel_name = message_info.get('channel_name')
        
        if not message_id or not channel_name:
            logger.warning(f"Received incomplete message data: {message_info}")
            return
        
        logger.info(f"Processing message {message_id} from channel '{channel_name}'")
        
        # Check if this message already exists in the database
        existing_message = Message.objects.filter(
            telegram_message_id=message_id,
            channel__name=channel_name
        ).exists()
        
        if existing_message:
            logger.info(f"Message {message_id} from '{channel_name}' already exists in database")
            return
        
        # Try to find the channel
        try:
            channel = Channel.objects.get(name=channel_name)
        except Channel.DoesNotExist:
            logger.error(f"Channel '{channel_name}' not found in database")
            return
        
        # Get session info if provided
        session = None
        session_id = message_info.get('session_id')
        if session_id:
            try:
                session = TelegramSession.objects.get(id=session_id)
            except TelegramSession.DoesNotExist:
                logger.warning(f"Session ID {session_id} not found in database")
        
        # Create message
        try:
            message = Message(
                text=message_info.get('text', ''),
                media=message_info.get('media', ''),
                media_type=message_info.get('media_type'),
                telegram_message_id=message_id,
                telegram_channel_id=message_info.get('channel_id'),
                telegram_link=message_info.get('link', ''),
                channel=channel,
                created_at=message_info.get('date') or timezone.now(),
                session_used=session
            )
            message.save()
            logger.info(f"Successfully saved message {message_id} from '{channel_name}' to database")
        except Exception as e:
            logger.error(f"Error saving message {message_id} from '{channel_name}': {e}")
            logger.error(traceback.format_exc())
    except Exception as e:
        logger.error(f"Error processing message: {e}")
        logger.error(traceback.format_exc())

class Command(BaseCommand):
    help = 'Start the Telethon parser for downloading messages from Telegram channels'
    
    def add_arguments(self, parser):
        parser.add_argument('--force', action='store_true', help='Force restart of the parser')
        parser.add_argument('--dryrun', action='store_true', help='Test connectivity without saving messages')
    
    def handle(self, *args, **options):
        force = options['force']
        dryrun = options['dryrun']
        
        # Check if session file exists
        session_file = 'telethon_user_session.session'
        if not os.path.exists(session_file):
            self.stdout.write(self.style.ERROR(f"Telethon session file '{session_file}' not found."))
            self.stdout.write(self.style.NOTICE("Please run 'python manage.py inittelethon' first to create a session."))
            sys.exit(1)
        
        # Check if any channels are configured
        channels_count = Channel.objects.count()
        active_channels = Channel.objects.filter(is_active=True).count()
        
        if channels_count == 0:
            self.stdout.write(self.style.WARNING("No channels found in the database."))
            self.stdout.write(self.style.NOTICE("Please add channels in the admin panel before running the parser."))
            sys.exit(1)
        
        if active_channels == 0:
            self.stdout.write(self.style.WARNING("No active channels found in the database."))
            self.stdout.write(self.style.NOTICE("Please activate at least one channel in the admin panel."))
            sys.exit(1)
        
        self.stdout.write(self.style.SUCCESS(f"Found {active_channels} active channels out of {channels_count} total channels."))
        
        # Check parser lock file to prevent multiple instances
        lock_file = 'telethon_parser.lock'
        if os.path.exists(lock_file) and not force:
            self.stdout.write(self.style.ERROR(f"Parser lock file '{lock_file}' exists, indicating another parser may be running."))
            self.stdout.write(self.style.NOTICE("Use --force to override if you're sure no other parser is running."))
            sys.exit(1)
        
        # Create lock file
        try:
            with open(lock_file, 'w') as f:
                f.write(str(os.getpid()))
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"Failed to create lock file: {e}"))
        
        try:
            self.stdout.write(self.style.SUCCESS('Starting the Telethon parser...'))
            
            # Create a queue for messages
            message_queue = multiprocessing.Queue()
            
            # Import here to avoid circular imports
            from tg_bot.telethon_worker import telethon_worker_process
            
            # Start the parser in a separate process
            telethon_process = multiprocessing.Process(
                target=telethon_worker_process,
                args=(message_queue,)
            )
            telethon_process.start()
            
            # Processing messages from the queue (will work in the main thread)
            try:
                self.stdout.write(self.style.SUCCESS(f'Parser started (PID: {telethon_process.pid})'))
                self.stdout.write('Press Ctrl+C to stop...')
                
                message_count = 0
                start_time = time.time()
                
                while telethon_process.is_alive():
                    try:
                        # Get a message from the queue (with a timeout to check the process status)
                        message = message_queue.get(block=True, timeout=1)
                        message_count += 1
                        
                        message_info = message.get('message_info', {})
                        msg_id = message_info.get('message_id', 'unknown')
                        channel = message_info.get('channel_name', 'unknown')
                        
                        self.stdout.write(f"Received message {msg_id} from channel '{channel}'")
                        
                        if not dryrun:
                            # Process the message in the main thread
                            process_message(message)
                        else:
                            self.stdout.write(self.style.WARNING(f"Dry run mode: Not saving message {msg_id} from '{channel}'"))
                        
                        # Report progress periodically
                        if message_count % 10 == 0:
                            elapsed = time.time() - start_time
                            rate = message_count / elapsed if elapsed > 0 else 0
                            self.stdout.write(self.style.SUCCESS(
                                f"Processed {message_count} messages in {elapsed:.1f} seconds ({rate:.2f} msgs/sec)"
                            ))
                    except queue.Empty:
                        # The queue is empty, continue waiting
                        pass
                    
            except KeyboardInterrupt:
                self.stdout.write(self.style.WARNING('Received a termination signal, stopping the parser...'))
            finally:
                # Stop the parser
                telethon_process.terminate()
                telethon_process.join(timeout=5)
                
                if telethon_process.is_alive():
                    self.stdout.write(self.style.WARNING('Parser did not terminate gracefully, killing...'))
                    telethon_process.kill()
                    telethon_process.join(timeout=5)
                
                # Report stats
                if message_count > 0:
                    elapsed = time.time() - start_time
                    rate = message_count / elapsed if elapsed > 0 else 0
                    self.stdout.write(self.style.SUCCESS(
                        f"Processed {message_count} messages in {elapsed:.1f} seconds ({rate:.2f} msgs/sec)"
                    ))
                
                self.stdout.write(self.style.SUCCESS('Parser stopped'))
        finally:
            # Remove lock file
            try:
                if os.path.exists(lock_file):
                    os.remove(lock_file)
            except Exception as e:
                self.stdout.write(self.style.ERROR(f"Failed to remove lock file: {e}")) 