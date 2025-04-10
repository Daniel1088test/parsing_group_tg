import asyncio
from django.core.management.base import BaseCommand
import logging

# configuration of logging
logger = logging.getLogger('django')

class Command(BaseCommand):
    help = 'Start the Telegram bot'
    
    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS('Starting the Telegram bot...'))
        
        try:
            loop = asyncio.get_event_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
        
        try:
            from tg_bot.bot import main
            loop.run_until_complete(main())
        except KeyboardInterrupt:
            self.stdout.write(self.style.WARNING('Received a termination signal, stopping the bot...'))
        except Exception as e:
            self.stderr.write(self.style.ERROR(f'Error: {e}'))
        finally:
            self.stdout.write(self.style.SUCCESS('Bot stopped')) 