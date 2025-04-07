import multiprocessing
import queue
from django.core.management.base import BaseCommand
import logging

# configuration of logging
logger = logging.getLogger('django')

class Command(BaseCommand):
    help = 'Start the Telethon parser'
    
    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS('Starting the Telethon parser...'))
        
        # create a queue for messages
        message_queue = multiprocessing.Queue()
        
        # start the parser in a separate process
        from tg_bot.telethon_worker import telethon_worker_process
        telethon_process = multiprocessing.Process(
            target=telethon_worker_process,
            args=(message_queue,)
        )
        telethon_process.start()
        
        # processing messages from the queue (will work in the main thread)
        try:
            self.stdout.write(self.style.SUCCESS(f'Parser started (PID: {telethon_process.pid})'))
            self.stdout.write('Press Ctrl+C to stop...')
            
            while telethon_process.is_alive():
                try:
                    # get a message from the queue (with a timeout to check the process status)
                    message = message_queue.get(block=True, timeout=1)
                    logger.info(f"Received a message with ID: {message.get('message_info', {}).get('message_id')}")
                except queue.Empty:
                    # the queue is empty, continue waiting
                    continue
        except KeyboardInterrupt:
            self.stdout.write(self.style.WARNING('Received a termination signal, stopping the parser...'))
        finally:
            # stop the parser
            telethon_process.terminate()
            telethon_process.join(timeout=5)
            self.stdout.write(self.style.SUCCESS('Parser stopped')) 