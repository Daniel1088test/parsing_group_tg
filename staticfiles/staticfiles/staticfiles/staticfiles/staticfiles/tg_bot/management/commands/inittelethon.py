import os
import asyncio
from django.core.management.base import BaseCommand
from telethon import TelegramClient
from tg_bot.config import API_ID, API_HASH

class Command(BaseCommand):
    help = 'Initialize Telethon session and verify connection'
    
    def add_arguments(self, parser):
        parser.add_argument('--force', action='store_true', help='Force creation of a new session')
        
    async def check_session(self, force=False):
        session_file = 'telethon_user_session'
        
        # Check if session exists
        session_exists = os.path.exists(f'{session_file}.session')
        
        if session_exists and force:
            self.stdout.write(self.style.WARNING(f'Removing existing session file: {session_file}.session'))
            os.remove(f'{session_file}.session')
            session_exists = False
        
        # If session doesn't exist or force is True, create a new one
        client = TelegramClient(session_file, API_ID, API_HASH)
        
        try:
            await client.connect()
            
            if await client.is_user_authorized():
                me = await client.get_me()
                self.stdout.write(self.style.SUCCESS(f'Session is valid! Authorized as: {me.first_name} (@{me.username}, ID: {me.id})'))
                self.stdout.write(self.style.SUCCESS(f'Session file: {session_file}.session'))
                
                # Get dialogs to verify connection
                dialogs = await client.get_dialogs(limit=5)
                self.stdout.write(self.style.SUCCESS(f'Successfully accessed {len(dialogs)} dialogs:'))
                for dialog in dialogs:
                    self.stdout.write(f'  • {dialog.name} ({dialog.entity.id})')
                
                return True
            else:
                self.stdout.write(self.style.WARNING('Session exists but is not authorized. Starting authorization...'))
                self.stdout.write(self.style.NOTICE('\nIMPORTANT: You must use a regular user account, NOT a bot account!'))
                self.stdout.write(self.style.NOTICE('Please enter your phone number when prompted.\n'))
                
                try:
                    await client.start()
                    me = await client.get_me()
                    self.stdout.write(self.style.SUCCESS(f'Successfully authorized as: {me.first_name} (@{me.username}, ID: {me.id})'))
                    self.stdout.write(self.style.SUCCESS(f'Session file saved as: {session_file}.session'))
                    return True
                except Exception as e:
                    self.stdout.write(self.style.ERROR(f'Error during authorization: {e}'))
                    return False
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'Error connecting to Telegram: {e}'))
            return False
        finally:
            await client.disconnect()
    
    def handle(self, *args, **options):
        force = options['force']
        
        self.stdout.write(self.style.NOTICE('Initializing Telethon session...'))
        success = asyncio.run(self.check_session(force))
        
        if success:
            self.stdout.write(self.style.SUCCESS('\nTelethon session is valid and ready to use!'))
            self.stdout.write(self.style.SUCCESS('You can now run the parser using: python manage.py runtelethon'))
        else:
            self.stdout.write(self.style.ERROR('\nFailed to initialize Telethon session.'))
            self.stdout.write(self.style.NOTICE('Try running with --force to create a new session: python manage.py inittelethon --force')) 