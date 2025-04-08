import os
import base64
import logging
import mimetypes
from django.core.management.base import BaseCommand
from admin_panel.models import TelegramSession, Message
from django.conf import settings
from pathlib import Path
import traceback
from django.db import DatabaseError
import django.db.models
import shutil

logger = logging.getLogger(__name__)

class Command(BaseCommand):
    help = 'Fix session authentication status and create placeholder media files'

    def add_arguments(self, parser):
        parser.add_argument('--force', action='store_true', help='Force update all sessions even if they appear authenticated')
        parser.add_argument('--media-only', action='store_true', help='Only fix media files, skip sessions')
        parser.add_argument('--sessions-only', action='store_true', help='Only fix sessions, skip media files')

    def handle(self, *args, **options):
        force = options.get('force', False)
        media_only = options.get('media_only', False)
        sessions_only = options.get('sessions_only', False)
        
        # Create directories first to avoid permission issues
        self.create_directories()
        
        if not sessions_only:
            self.fix_media_files()
        
        if not media_only:
            self.fix_sessions(force)
            
        self.stdout.write(self.style.SUCCESS('Completed fixing sessions and media files'))
    
    def create_directories(self):
        """Create necessary directories with proper permissions"""
        dirs_to_create = [
            os.path.join(settings.MEDIA_ROOT),
            os.path.join(settings.MEDIA_ROOT, 'messages'),
            os.path.join(settings.STATIC_ROOT, 'img'),
            'data/sessions'
        ]
        
        for directory in dirs_to_create:
            try:
                os.makedirs(directory, exist_ok=True)
                self.stdout.write(f'Ensured directory exists: {directory}')
                
                # Set directory permissions to 0755
                try:
                    os.chmod(directory, 0o755)
                    self.stdout.write(f'Set directory permissions for: {directory}')
                except Exception as e:
                    self.stdout.write(self.style.WARNING(f'Could not set permissions on directory {directory}: {e}'))
            except Exception as e:
                self.stdout.write(self.style.ERROR(f'Error creating directory {directory}: {e}'))

    def fix_sessions(self, force=False):
        """Fix session authentication status in the database"""
        self.stdout.write('Checking and fixing Telegram sessions...')
        
        try:
            # Get all sessions
            sessions = TelegramSession.objects.all()
            self.stdout.write(f'Found {len(sessions)} sessions in database')
            
            fixed_count = 0
            
            # Check each session
            for session in sessions:
                self.stdout.write(f'Processing session {session.id} ({session.phone})...')
                
                # Skip if already marked as authenticated and we're not forcing
                if not force:
                    try:
                        # Check if needs_auth field exists and is False
                        if hasattr(session, 'needs_auth') and not session.needs_auth:
                            self.stdout.write(f'  Session {session.id} is already marked as authenticated')
                            continue
                    except (AttributeError, DatabaseError):
                        # Field might not exist in database yet
                        self.stdout.write(f'  Session {session.id} needs to be checked (needs_auth field not available)')
                
                # Check for session files
                if session.session_file:
                    session_paths = [
                        f"{session.session_file}.session",
                        f"data/sessions/{session.session_file}.session"
                    ]
                    
                    file_found = False
                    for path in session_paths:
                        if os.path.exists(path):
                            self.stdout.write(f'  Found session file: {path}')
                            
                            # Set permissions on the session file
                            try:
                                os.chmod(path, 0o644)
                                self.stdout.write(f'  Set permissions for session file: {path}')
                            except Exception as e:
                                self.stdout.write(self.style.WARNING(f'  Could not set permissions for {path}: {e}'))
                                
                            file_found = True
                            break
                    
                    if file_found:
                        try:
                            # Update session if we have needs_auth field
                            if hasattr(session, 'needs_auth'):
                                session.needs_auth = False
                                session.save(update_fields=['needs_auth'])
                                fixed_count += 1
                                self.stdout.write(self.style.SUCCESS(f'  Fixed session {session.id} based on session file'))
                        except (AttributeError, DatabaseError):
                            self.stdout.write(f'  Cannot update needs_auth for session {session.id} (field not in database)')
                
                # Check session data in database
                try:
                    if hasattr(session, 'session_data') and session.session_data:
                        self.stdout.write(f'  Session {session.id} has encoded session data')
                        
                        # Try to restore the session file from the data
                        try:
                            session_data = base64.b64decode(session.session_data)
                            session_file_path = f"data/sessions/telethon_session_{session.phone.replace('+', '')}.session"
                            
                            # Create the directory if it doesn't exist
                            os.makedirs(os.path.dirname(session_file_path), exist_ok=True)
                            
                            # Write the session data to a file
                            with open(session_file_path, 'wb') as f:
                                f.write(session_data)
                                
                            # Set file permissions
                            os.chmod(session_file_path, 0o644)
                            
                            # Update the session in the database
                            session.session_file = f"data/sessions/telethon_session_{session.phone.replace('+', '')}"
                            if hasattr(session, 'needs_auth'):
                                session.needs_auth = False
                            session.save()
                            
                            self.stdout.write(self.style.SUCCESS(f'  Restored session file from data: {session_file_path}'))
                        except Exception as e:
                            self.stdout.write(self.style.ERROR(f'  Error restoring session file: {e}'))
                        
                        fixed_count += 1
                    else:
                        self.stdout.write(f'  Session {session.id} has no encoded data')
                except (AttributeError, DatabaseError):
                    self.stdout.write(f'  Cannot check session_data for session {session.id} (field not in database)')
            
            self.stdout.write(self.style.SUCCESS(f'Fixed {fixed_count} sessions'))
            
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'Error in fix_sessions: {e}'))
            self.stdout.write(self.style.ERROR(f'Traceback: {traceback.format_exc()}'))
    
    def create_placeholder_image(self, filename, text="PLACEHOLDER"):
        """Create a simple placeholder image with PIL"""
        try:
            from PIL import Image, ImageDraw, ImageFont
            
            # Create a blank image with white background
            img = Image.new('RGB', (300, 200), color=(240, 240, 240))
            draw = ImageDraw.Draw(img)
            
            # Draw a border
            draw.rectangle([(0, 0), (299, 199)], outline=(200, 200, 200), width=2)
            
            # Add text
            draw.text((150, 100), text, fill=(100, 100, 100), anchor="mm")
            
            # Save the image
            img.save(filename)
            
            # Set permissions
            os.chmod(filename, 0o644)
            
            self.stdout.write(f'Created placeholder image: {filename}')
        except ImportError:
            # If PIL is not available, create an empty file
            with open(filename, 'wb') as f:
                f.write(b'')
            self.stdout.write(f'Created empty placeholder file: {filename} (PIL not available)')

    def fix_media_files(self):
        """Create placeholder files for missing media"""
        self.stdout.write('Checking and fixing media files...')
        
        # Create media directory if it doesn't exist
        media_dir = os.path.join(settings.MEDIA_ROOT, 'messages')
        os.makedirs(media_dir, exist_ok=True)
        self.stdout.write(f'Ensured media directory exists: {media_dir}')
        
        # Create placeholders directory if it doesn't exist
        placeholder_dir = os.path.join(settings.STATIC_ROOT, 'img')
        os.makedirs(placeholder_dir, exist_ok=True)
        self.stdout.write(f'Ensured placeholder directory exists: {placeholder_dir}')
        
        # Create placeholder images if they don't exist
        image_placeholder = os.path.join(placeholder_dir, 'placeholder-image.png')
        video_placeholder = os.path.join(placeholder_dir, 'placeholder-video.png')
        
        if not os.path.exists(image_placeholder):
            # Create a simple placeholder image
            self.create_placeholder_image(image_placeholder, "IMAGE")
            
        if not os.path.exists(video_placeholder):
            # Create a simple placeholder image for videos
            self.create_placeholder_image(video_placeholder, "VIDEO")
        
        try:
            # Get all messages with media
            messages = Message.objects.exclude(media__isnull=True).exclude(media='')
            self.stdout.write(f'Found {len(messages)} messages with media')
            
            fixed_count = 0
            
            for message in messages:
                try:
                    if not message.media:
                        continue
                        
                    # Get the media file path - handle FieldFile objects properly
                    media_path_str = str(message.media)
                    self.stdout.write(f'Processing media: {media_path_str} (type: {type(message.media)})')
                    
                    media_path = os.path.join(settings.MEDIA_ROOT, media_path_str)
                    
                    # Check if the file exists
                    if not os.path.exists(media_path):
                        self.stdout.write(f'  Media file not found: {media_path}')
                        
                        # Create appropriate placeholder based on media type
                        if message.media_type in ['photo', 'image', 'gif']:
                            placeholder = image_placeholder
                        elif message.media_type in ['video', 'document']:
                            placeholder = video_placeholder
                        else:
                            placeholder = image_placeholder
                        
                        # Create the directory if needed
                        dir_path = os.path.dirname(media_path)
                        os.makedirs(dir_path, exist_ok=True)
                        self.stdout.write(f'  Ensured directory exists: {dir_path}')
                        
                        try:
                            # Copy the placeholder file to the media location
                            shutil.copy2(placeholder, media_path)
                            
                            # Set file permissions
                            os.chmod(media_path, 0o644)
                            
                            self.stdout.write(f'  Created placeholder for {media_path_str}')
                            fixed_count += 1
                        except Exception as e:
                            self.stdout.write(self.style.ERROR(f'  Error creating placeholder: {e}'))
                            self.stdout.write(self.style.ERROR(f'  Traceback: {traceback.format_exc()}'))
                    else:
                        # File exists, but ensure permissions are correct
                        try:
                            os.chmod(media_path, 0o644)
                            self.stdout.write(f'  Set permissions for existing file: {media_path}')
                        except Exception as e:
                            self.stdout.write(self.style.WARNING(f'  Could not set permissions for {media_path}: {e}'))
                except Exception as e:
                    self.stdout.write(self.style.ERROR(f'Error processing message {message.id}: {e}'))
                    self.stdout.write(self.style.ERROR(f'Traceback: {traceback.format_exc()}'))
            
            self.stdout.write(self.style.SUCCESS(f'Fixed {fixed_count} media files'))
            
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'Error in fix_media_files: {e}'))
            self.stdout.write(self.style.ERROR(f'Traceback: {traceback.format_exc()}'))