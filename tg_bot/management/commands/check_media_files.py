import os
import shutil
import logging
from django.core.management.base import BaseCommand
from django.conf import settings
from admin_panel.models import Message

logger = logging.getLogger(__name__)

class Command(BaseCommand):
    help = 'Check and fix media files in the database and filesystem'

    def add_arguments(self, parser):
        parser.add_argument(
            '--fix',
            action='store_true',
            help='Fix issues with media files',
        )

    def handle(self, *args, **options):
        fix_enabled = options['fix']
        action_text = "Fixing" if fix_enabled else "Checking"
        self.stdout.write(self.style.SUCCESS(f"{action_text} media files..."))
        
        # Ensure media directories exist
        media_root = settings.MEDIA_ROOT
        messages_dir = os.path.join(media_root, 'messages')
        
        if not os.path.exists(media_root):
            self.stdout.write(self.style.WARNING(f"Media root directory doesn't exist: {media_root}"))
            if fix_enabled:
                os.makedirs(media_root, exist_ok=True)
                self.stdout.write(self.style.SUCCESS(f"Created media root directory: {media_root}"))
        
        if not os.path.exists(messages_dir):
            self.stdout.write(self.style.WARNING(f"Messages directory doesn't exist: {messages_dir}"))
            if fix_enabled:
                os.makedirs(messages_dir, exist_ok=True)
                self.stdout.write(self.style.SUCCESS(f"Created messages directory: {messages_dir}"))
        
        # Get all messages with media
        messages = Message.objects.exclude(media='').order_by('-created_at')
        self.stdout.write(f"Found {len(messages)} messages with media")
        
        # Stats
        missing_count = 0
        valid_count = 0
        fixed_count = 0
        
        # Check each message's media
        for message in messages:
            media_path = message.media
            
            # Get absolute path to the media file
            if media_path.startswith('/'):
                abs_path = media_path
            else:
                abs_path = os.path.join(settings.MEDIA_ROOT, media_path)
            
            # Fix common path issues
            if not media_path.startswith('messages/') and not fix_enabled:
                self.stdout.write(self.style.WARNING(f"Media path doesn't start with 'messages/': {media_path}"))
                missing_count += 1
            elif not os.path.exists(abs_path):
                self.stdout.write(self.style.WARNING(f"Media file not found: {abs_path}"))
                missing_count += 1
                
                if fix_enabled:
                    # Try to fix the path
                    if media_path.startswith('media/messages/'):
                        # Remove 'media/' prefix
                        new_path = media_path[6:]  # media/ = 6 chars
                        new_abs_path = os.path.join(settings.MEDIA_ROOT, new_path)
                        
                        if os.path.exists(new_abs_path):
                            message.media = new_path
                            message.save(update_fields=['media'])
                            self.stdout.write(self.style.SUCCESS(f"Fixed path: {media_path} -> {new_path}"))
                            fixed_count += 1
                        else:
                            # Try to find file by message ID in the messages directory
                            message_id = os.path.basename(media_path).split('_')[0]
                            
                            found = False
                            for filename in os.listdir(messages_dir):
                                if filename.startswith(f"{message_id}_"):
                                    new_path = f"messages/{filename}"
                                    message.media = new_path
                                    message.save(update_fields=['media'])
                                    self.stdout.write(self.style.SUCCESS(f"Found file by ID: {media_path} -> {new_path}"))
                                    fixed_count += 1
                                    found = True
                                    break
                                    
                            if not found:
                                # Clear the media path if file is not found
                                self.stdout.write(self.style.WARNING(f"Could not find replacement for {media_path}, clearing field"))
                                message.media = ''
                                message.save(update_fields=['media'])
                    else:
                        # Set correct path format
                        filename = os.path.basename(media_path)
                        if filename:
                            new_path = f"messages/{filename}"
                            new_abs_path = os.path.join(settings.MEDIA_ROOT, new_path)
                            
                            # Check if file exists with the new path
                            if os.path.exists(new_abs_path):
                                message.media = new_path
                                message.save(update_fields=['media'])
                                self.stdout.write(self.style.SUCCESS(f"Fixed path: {media_path} -> {new_path}"))
                                fixed_count += 1
                            else:
                                # Path format was wrong but file still doesn't exist
                                self.stdout.write(self.style.WARNING(f"Could not find file for {media_path} at {new_abs_path}"))
                                message.media = ''
                                message.save(update_fields=['media'])
            else:
                valid_count += 1
        
        # Check for orphaned files in the messages directory
        if os.path.exists(messages_dir):
            known_files = set()
            for message in messages:
                if message.media and message.media.startswith('messages/'):
                    known_files.add(os.path.basename(message.media))
            
            orphaned_files = []
            for filename in os.listdir(messages_dir):
                if filename not in known_files and not filename.endswith('.session'):
                    orphaned_files.append(filename)
            
            if orphaned_files:
                self.stdout.write(self.style.WARNING(f"Found {len(orphaned_files)} orphaned files in messages directory"))
                for filename in orphaned_files[:10]:  # Show first 10
                    self.stdout.write(f"  - {filename}")
                
                if len(orphaned_files) > 10:
                    self.stdout.write(f"  - ... and {len(orphaned_files) - 10} more")
        
        self.stdout.write(self.style.SUCCESS(
            f"\nMedia check complete!\n"
            f"Valid files: {valid_count}\n"
            f"Missing files: {missing_count}\n"
            f"Fixed files: {fixed_count if fix_enabled else 'N/A (use --fix option to fix)'}"
        )) 