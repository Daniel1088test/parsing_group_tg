import os
import asyncio
import logging
from django.core.management.base import BaseCommand
from django.utils import timezone
from admin_panel.models import TelegramSession
from tg_bot.auth_telethon import verify_session, verify_all_sessions_in_db
from datetime import timedelta

class Command(BaseCommand):
    help = 'Verify all Telegram sessions and mark those that need authentication'
    
    def add_arguments(self, parser):
        parser.add_argument(
            '--full',
            action='store_true',
            help='Perform full verification including session content',
        )
        parser.add_argument(
            '--session-id',
            type=int,
            help='Verify only a specific session ID',
        )
        parser.add_argument(
            '--update',
            action='store_true',
            help='Update session files paths in database if found',
        )
        
    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS('Starting Telegram session verification...'))
        
        # Run the async verification
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        try:
            if options['session_id']:
                # Verify specific session
                session_id = options['session_id']
                self.stdout.write(f"Verifying session ID: {session_id}")
                result = loop.run_until_complete(self.verify_session(session_id, options['update']))
                if result:
                    self.stdout.write(self.style.SUCCESS(f"Session {session_id} is valid"))
                else:
                    self.stdout.write(self.style.ERROR(f"Session {session_id} needs authentication"))
            else:
                # Verify all sessions
                results = loop.run_until_complete(verify_all_sessions_in_db())
                
                valid_count = sum(1 for r in results if r['authorized'])
                invalid_count = len(results) - valid_count
                
                self.stdout.write(self.style.SUCCESS(f"Verification complete: {valid_count} valid, {invalid_count} need authentication"))
                
                # Print details
                for result in results:
                    status = self.style.SUCCESS("✓ Valid") if result['authorized'] else self.style.ERROR("✗ Needs Auth")
                    self.stdout.write(f"Session {result['session_id']} ({result['phone']}): {status}")
                    
                # Update last verified timestamp for all sessions
                TelegramSession.objects.all().update(updated_at=timezone.now())
                
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"Error during verification: {str(e)}"))
        finally:
            loop.close()
            
    async def verify_session(self, session_id, update=False):
        """Verify a specific session"""
        try:
            session = TelegramSession.objects.get(id=session_id)
            
            # Check if session file exists
            if session.session_file and os.path.exists(f"{session.session_file}.session"):
                # Verify the session file
                from tg_bot.config import API_ID, API_HASH
                is_valid, user_info = await verify_session(session.session_file, API_ID, API_HASH)
                
                if is_valid:
                    session.needs_auth = False
                    session.save(update_fields=['needs_auth', 'updated_at'])
                    return True
                else:
                    session.needs_auth = True
                    session.save(update_fields=['needs_auth', 'updated_at'])
                    return False
            else:
                # Look for session files with various naming patterns
                potential_session_files = [
                    f"telethon_session_{session_id}",
                    f"telethon_session_{session.phone.replace('+', '')}",
                    f"telethon_user_session_{session_id}",
                    f"session_{session_id}",
                ]
                
                # Check in standard locations
                session_dirs = [".", "data/sessions", "sessions", "/app/data/sessions"]
                
                for directory in session_dirs:
                    if not os.path.exists(directory):
                        continue
                        
                    for base_name in potential_session_files:
                        full_path = os.path.join(directory, base_name)
                        if os.path.exists(f"{full_path}.session"):
                            # Verify the session file
                            from tg_bot.config import API_ID, API_HASH
                            is_valid, user_info = await verify_session(full_path, API_ID, API_HASH)
                            
                            if is_valid:
                                # If update flag is set, update the session file path
                                if update:
                                    session.session_file = full_path
                                    session.needs_auth = False
                                    session.save(update_fields=['session_file', 'needs_auth', 'updated_at'])
                                return True
                
                # No valid session found
                session.needs_auth = True
                if update:
                    session.session_file = None
                    session.save(update_fields=['session_file', 'needs_auth', 'updated_at'])
                else:
                    session.save(update_fields=['needs_auth', 'updated_at'])
                return False
                
        except TelegramSession.DoesNotExist:
            self.stdout.write(self.style.ERROR(f"Session ID {session_id} not found"))
            return False
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"Error verifying session {session_id}: {str(e)}"))
            return False 