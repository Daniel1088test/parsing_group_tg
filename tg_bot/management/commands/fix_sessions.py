import os
import base64
import logging
import mimetypes
from django.core.management.base import BaseCommand
from admin_panel.models import TelegramSession, Message
from django.conf import settings
from pathlib import Path

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
        
        if not sessions_only:
            self.fix_media_files()
        
        if not media_only:
            self.fix_sessions(force)
            
        self.stdout.write(self.style.SUCCESS('Completed fixing sessions and media files'))

    def fix_sessions(self, force=False):
        """Fix session authentication status in the database"""
        self.stdout.write('Checking and fixing Telegram sessions...')
        
        # Get all sessions
        sessions = TelegramSession.objects.all()
        self.stdout.write(f'Found {len(sessions)} sessions in database')
        
        fixed_count = 0
        
        for session in sessions:
            self.stdout.write(f'Processing session {session.id} ({session.phone})...')
            
            # Skip if already marked as authenticated and we're not forcing
            if not force and hasattr(session, 'needs_auth') and not session.needs_auth:
                self.stdout.write(f'  Session {session.id} is already marked as authenticated')
                continue
                
            # Check if session has encoded session data
            if session.session_data:
                self.stdout.write(f'  Session {session.id} has encoded session data')
                
                # Restore session file from encoded data
                try:
                    # Decode the session data
                    session_data = base64.b64decode(session.session_data)
                    
                    # Determine session file path
                    if session.session_file:
                        session_path = session.session_file
                    else:
                        session_path = f"telethon_session_{session.phone.replace('+', '')}"
                        
                    # Create parent directories if needed
                    os.makedirs('data/sessions', exist_ok=True)
                    
                    # Always write to both locations for redundancy
                    paths = [
                        f"{session_path}.session",
                        f"data/sessions/{session_path}.session"
                    ]
                    
                    for path in paths:
                        with open(path, 'wb') as f:
                            f.write(session_data)
                        self.stdout.write(f'  Restored session file to {path}')
                    
                    # Update the session in database
                    session.needs_auth = False
                    session.save(update_fields=['needs_auth'])
                    
                    fixed_count += 1
                    self.stdout.write(self.style.SUCCESS(f'  Fixed session {session.id}'))
                except Exception as e:
                    self.stdout.write(self.style.ERROR(f'  Error restoring session from database: {e}'))
            else:
                self.stdout.write(self.style.WARNING(f'  Session {session.id} has no encoded data'))
        
        self.stdout.write(self.style.SUCCESS(f'Fixed {fixed_count} sessions'))

    def fix_media_files(self):
        """Create placeholder files for missing media"""
        self.stdout.write('Checking and fixing media files...')
        
        # Create media directory if it doesn't exist
        media_dir = os.path.join(settings.MEDIA_ROOT, 'messages')
        os.makedirs(media_dir, exist_ok=True)
        
        # Create placeholders directory if it doesn't exist
        placeholder_dir = os.path.join(settings.STATIC_ROOT, 'img')
        os.makedirs(placeholder_dir, exist_ok=True)
        
        # Create placeholder images if they don't exist
        image_placeholder = os.path.join(placeholder_dir, 'placeholder-image.png')
        video_placeholder = os.path.join(placeholder_dir, 'placeholder-video.png')
        
        if not os.path.exists(image_placeholder):
            # Create a simple placeholder image
            self.create_placeholder_image(image_placeholder, "IMAGE")
            
        if not os.path.exists(video_placeholder):
            # Create a simple placeholder image for videos
            self.create_placeholder_image(video_placeholder, "VIDEO")
        
        # Get all messages with media
        messages = Message.objects.exclude(media__isnull=True).exclude(media='')
        self.stdout.write(f'Found {len(messages)} messages with media')
        
        fixed_count = 0
        
        for message in messages:
            if not message.media:
                continue
                
            # Get the media file path
            media_path = os.path.join(settings.MEDIA_ROOT, message.media)
            
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
                os.makedirs(os.path.dirname(media_path), exist_ok=True)
                
                try:
                    # Copy the placeholder file to the media location
                    import shutil
                    shutil.copy2(placeholder, media_path)
                    self.stdout.write(f'  Created placeholder for {message.media}')
                    fixed_count += 1
                except Exception as e:
                    self.stdout.write(self.style.ERROR(f'  Error creating placeholder: {e}'))
        
        self.stdout.write(self.style.SUCCESS(f'Fixed {fixed_count} media files'))

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
            self.stdout.write(f'Created placeholder image: {filename}')
        except ImportError:
            # If PIL is not available, create an empty file
            with open(filename, 'wb') as f:
                f.write(b'')
            self.stdout.write(f'Created empty placeholder file: {filename} (PIL not available)') 