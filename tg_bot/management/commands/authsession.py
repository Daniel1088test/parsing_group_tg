import os
import asyncio
from django.core.management.base import BaseCommand, CommandError
from tg_bot.auth_telethon import create_session_file, verify_session, verify_all_sessions_in_db
from admin_panel.models import TelegramSession
from django.db.models import Q
from tg_bot.config import API_ID, API_HASH
from asgiref.sync import sync_to_async

class Command(BaseCommand):
    help = 'Authenticate Telegram sessions for message parsing'
    
    def add_arguments(self, parser):
        parser.add_argument('--phone', type=str, help='Phone number to authenticate (with country code, e.g. +380123456789)')
        parser.add_argument('--list', action='store_true', help='List all sessions and their status')
        parser.add_argument('--verify-all', action='store_true', help='Verify all sessions in the database')
        parser.add_argument('--verify', type=int, help='Verify a specific session by ID')
        parser.add_argument('--auth', type=int, help='Authenticate a specific session by ID')
    
    async def verify_db_sessions(self):
        """Verify all sessions in the database"""
        self.stdout.write(self.style.NOTICE('Verifying all sessions in the database...'))
        results = await verify_all_sessions_in_db()
        
        valid_count = sum(1 for r in results if r['authorized'])
        total = len(results)
        
        self.stdout.write(self.style.SUCCESS(f'\n{valid_count}/{total} sessions are valid\n'))
        
        for result in results:
            if result['authorized']:
                user_info = result['user_info']
                username = f"@{user_info.get('username')}" if user_info.get('username') else "No username"
                self.stdout.write(self.style.SUCCESS(
                    f"✓ Session {result['session_id']} ({result['phone']}) - {user_info.get('first_name')} {username}"
                ))
            else:
                self.stdout.write(self.style.ERROR(
                    f"✗ Session {result['session_id']} ({result['phone']}) - Not authorized"
                ))
        return results
    
    @sync_to_async
    def get_session_by_id(self, session_id):
        """Get a session by ID"""
        try:
            return TelegramSession.objects.get(id=session_id)
        except TelegramSession.DoesNotExist:
            return None
    
    @sync_to_async
    def get_session_by_phone(self, phone):
        """Get a session by phone number"""
        return TelegramSession.objects.filter(phone=phone).first()
    
    @sync_to_async
    def create_session_record(self, phone, api_id, api_hash):
        """Create a new session record"""
        # Check if needs_auth field exists
        has_needs_auth = hasattr(TelegramSession, 'needs_auth')
        
        # Create session data
        session_data = {
            'phone': phone,
            'api_id': api_id,
            'api_hash': api_hash,
            'is_active': True,
        }
        
        # Add needs_auth only if the field exists
        if has_needs_auth:
            session_data['needs_auth'] = True
            
        session = TelegramSession(**session_data)
        session.save()
        return session
    
    @sync_to_async
    def update_session(self, session, session_file=None, needs_auth=None):
        """Update a session record"""
        if session_file is not None:
            session.session_file = session_file
        
        # Only update needs_auth if field exists
        if needs_auth is not None and hasattr(session, 'needs_auth'):
            session.needs_auth = needs_auth
            
        session.save()
        return session
    
    async def verify_single_session(self, session_id):
        """Verify a single session by ID"""
        session = await self.get_session_by_id(session_id)
        if not session:
            self.stdout.write(self.style.ERROR(f"Session with ID {session_id} does not exist"))
            return False
            
        self.stdout.write(self.style.NOTICE(f'Verifying session {session_id} ({session.phone})...'))
        
        # Check possible session paths
        possible_paths = [
            session.session_file,
            f"telethon_session_{session_id}",
            f"telethon_session_{session.phone.replace('+', '')}",
            f"data/sessions/telethon_session_{session.phone.replace('+', '')}",
        ]
        
        for path in [p for p in possible_paths if p]:
            if os.path.exists(f"{path}.session"):
                self.stdout.write(self.style.NOTICE(f'Testing session file: {path}.session'))
                is_valid, user_info = await verify_session(path, API_ID, API_HASH)
                
                if is_valid:
                    username = f"@{user_info.get('username')}" if user_info.get('username') else "No username"
                    self.stdout.write(self.style.SUCCESS(
                        f"✓ Session {session_id} ({session.phone}) - {user_info.get('first_name')} {username}"
                    ))
                    
                    # Update the session in the database
                    await self.update_session(session, session_file=path, needs_auth=False)
                    
                    self.stdout.write(self.style.SUCCESS(f'Updated session file path in database: {path}'))
                    return True
        
        self.stdout.write(self.style.ERROR(f"✗ No valid session file found for {session.phone}"))
        
        # Only update needs_auth if the field exists
        if hasattr(session, 'needs_auth'):
            await self.update_session(session, needs_auth=True)
        else:
            # Otherwise just ensure session_file is None
            await self.update_session(session, session_file=None)
            
        return False
    
    async def authenticate_session(self, session_id=None, phone=None):
        """Authenticate a session by ID or phone number"""
        if session_id:
            session = await self.get_session_by_id(session_id)
            if not session:
                self.stdout.write(self.style.ERROR(f"Session with ID {session_id} does not exist"))
                return False
            phone = session.phone
        elif phone:
            # Check if session already exists for this phone
            session = await self.get_session_by_phone(phone)
            if not session:
                # Create a new session record
                session = await self.create_session_record(phone, API_ID, API_HASH)
                self.stdout.write(self.style.SUCCESS(f"Created new session record for {phone}"))
        else:
            self.stdout.write(self.style.ERROR("Please provide either a session ID or phone number"))
            return False
            
        self.stdout.write(self.style.NOTICE(f'Starting authentication for {phone} (ID: {session.id})...'))
        
        # Define session filename
        session_name = f"telethon_session_{phone.replace('+', '')}"
        
        # Create directories if they don't exist
        os.makedirs('data/sessions', exist_ok=True)
        
        # Create the session
        success = await create_session_file(phone, API_ID, API_HASH, session_name, interactive=True)
        
        if success:
            self.stdout.write(self.style.SUCCESS(f"✓ Successfully authenticated session for {phone}"))
            
            # Update the session in the database
            await self.update_session(session, session_file=session_name, needs_auth=False)
            
            # Copy the session file to ensure it's available
            src_file = f"{session_name}.session"
            dst_file = f"data/sessions/{session_name}.session"
            
            if os.path.exists(src_file):
                import shutil
                try:
                    shutil.copy2(src_file, dst_file)
                    self.stdout.write(self.style.SUCCESS(f"Session file copied to {dst_file}"))
                except Exception as e:
                    self.stdout.write(self.style.WARNING(f"Error copying session file: {e}"))
            
            return True
        else:
            self.stdout.write(self.style.ERROR(f"✗ Failed to authenticate session for {phone}"))
            
            # Only update needs_auth if the field exists
            if hasattr(session, 'needs_auth'):
                await self.update_session(session, needs_auth=True)
            else:
                # Make sure session_file is None to indicate it's not authenticated
                await self.update_session(session, session_file=None)
                
            return False
    
    @sync_to_async
    def list_sessions_db(self):
        """Get all sessions from database"""
        return list(TelegramSession.objects.all().order_by('id'))

    async def list_sessions(self):
        """List all sessions in the database"""
        sessions = await self.list_sessions_db()
        
        if not sessions:
            self.stdout.write(self.style.NOTICE("No sessions found in the database"))
            return
            
        self.stdout.write(self.style.NOTICE("\nTelegram Sessions:"))
        self.stdout.write("─" * 60)
        self.stdout.write(f"{'ID':4} | {'Phone':15} | {'Status':8} | {'Auth':8} | {'Session File'}")
        self.stdout.write("─" * 60)
        
        for session in sessions:
            status = "Active" if session.is_active else "Inactive"
            auth = "Needed" if session.needs_auth else "OK"
            self.stdout.write(
                f"{session.id:4} | {session.phone:15} | {status:8} | {auth:8} | {session.session_file or 'None'}"
            )
        
        self.stdout.write("─" * 60)
        self.stdout.write(self.style.NOTICE("\nTo authenticate a session:"))
        self.stdout.write("python manage.py authsession --auth SESSION_ID")
        self.stdout.write("\nTo authenticate with a new phone number:")
        self.stdout.write("python manage.py authsession --phone +PHONE_NUMBER")
    
    def handle(self, *args, **options):
        """Main command handler"""
        if options['list']:
            # List all sessions
            asyncio.run(self.list_sessions())
            return
            
        if options['verify_all']:
            # Verify all sessions
            asyncio.run(self.verify_db_sessions())
            return
            
        if options['verify']:
            # Verify a specific session
            asyncio.run(self.verify_single_session(options['verify']))
            return
            
        if options['auth']:
            # Authenticate a specific session
            asyncio.run(self.authenticate_session(session_id=options['auth']))
            return
            
        if options['phone']:
            # Authenticate with a phone number
            asyncio.run(self.authenticate_session(phone=options['phone']))
            return
            
        # If no specific option, show help
        self.stdout.write(self.style.NOTICE("Please specify an action:"))
        self.stdout.write("--list: List all sessions")
        self.stdout.write("--verify-all: Check all sessions")
        self.stdout.write("--verify ID: Check a specific session")
        self.stdout.write("--auth ID: Authenticate a session")
        self.stdout.write("--phone NUMBER: Authenticate with a phone number") 