import os
import base64
import logging
from django.core.management.base import BaseCommand, CommandError
from admin_panel.models import TelegramSession
from tg_bot.config import API_ID, API_HASH

logger = logging.getLogger(__name__)

class Command(BaseCommand):
    help = 'Encode an existing Telethon session file to the database'

    def add_arguments(self, parser):
        parser.add_argument('session_file', type=str, help='Path to the session file')
        parser.add_argument('--phone', type=str, default='telethon_main', help='Phone number identifier for the session')
        parser.add_argument('--active', action='store_true', help='Set session as active')

    def handle(self, *args, **options):
        session_file = options['session_file']
        phone = options['phone']
        is_active = options['active']
        
        if not os.path.exists(session_file):
            raise CommandError(f'Session file "{session_file}" does not exist')
        
        try:
            # Read and encode the session file
            with open(session_file, 'rb') as f:
                session_data = f.read()
                encoded_data = base64.b64encode(session_data).decode('utf-8')
            
            # Get file name without extension
            session_name = os.path.splitext(os.path.basename(session_file))[0]
            
            # Save to database
            session, created = TelegramSession.objects.update_or_create(
                phone=phone,
                defaults={
                    'api_id': API_ID,
                    'api_hash': API_HASH,
                    'session_file': session_name,
                    'session_data': encoded_data,
                    'is_active': is_active
                }
            )
            
            action = 'Created' if created else 'Updated'
            self.stdout.write(self.style.SUCCESS(f'{action} session for phone "{phone}"'))
            self.stdout.write(f'Session file: {session_file}')
            self.stdout.write(f'Encoded length: {len(encoded_data)} characters')
            self.stdout.write(f'Active: {is_active}')
            
            # Also copy to standard session names for redundancy
            standard_names = ['telethon_session.session', 'telethon_session_backup.session']
            for std_name in standard_names:
                if os.path.basename(session_file) != std_name:
                    import shutil
                    try:
                        shutil.copy(session_file, std_name)
                        self.stdout.write(f'Copied to {std_name} for redundancy')
                    except Exception as e:
                        self.stdout.write(self.style.WARNING(f'Warning: Could not copy to {std_name}: {e}'))
            
            return
            
        except Exception as e:
            raise CommandError(f'Error encoding session: {e}') 