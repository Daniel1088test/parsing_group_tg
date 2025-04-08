import os
import logging
from django.core.management.base import BaseCommand
from django.conf import settings
from admin_panel.models import Message

logger = logging.getLogger(__name__)

class Command(BaseCommand):
    help = 'Fix media paths in the database to ensure they are correctly stored'

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS('Starting media path fix...'))
        
        # Get all messages with media
        messages = Message.objects.exclude(media='').order_by('-created_at')
        
        self.stdout.write(f'Found {len(messages)} messages with media')
        
        # Count of fixed messages
        fixed_count = 0
        errors_count = 0
        
        for message in messages:
            try:
                # Current media path
                current_path = message.media
                
                # Skip if already correct format (messages/filename.ext)
                if current_path.startswith('messages/') and not current_path.startswith('media/'):
                    # Check if file exists
                    full_path = os.path.join(settings.MEDIA_ROOT, current_path)
                    if os.path.exists(full_path):
                        self.stdout.write(f'Media file exists: {current_path}')
                        continue
                
                # Fix common path issues
                if current_path.startswith('media/messages/'):
                    # Remove 'media/' prefix
                    new_path = current_path[6:]  # Remove 'media/'
                elif not current_path.startswith('messages/'):
                    # Add 'messages/' prefix if not present
                    new_path = f'messages/{os.path.basename(current_path)}'
                else:
                    # Already correct format
                    new_path = current_path
                
                # Check if the file exists in the new path
                full_path = os.path.join(settings.MEDIA_ROOT, new_path)
                
                if os.path.exists(full_path):
                    # Update the path in the database
                    self.stdout.write(f'Updating path: {current_path} -> {new_path}')
                    message.media = new_path
                    message.save(update_fields=['media'])
                    fixed_count += 1
                else:
                    # File doesn't exist, try to find it by ID
                    file_id = os.path.basename(current_path).split('_')[0]
                    self.stdout.write(f'File not found, searching for ID {file_id} in media directory')
                    
                    # Search in messages directory for matching ID
                    found = False
                    for filename in os.listdir(os.path.join(settings.MEDIA_ROOT, 'messages')):
                        if filename.startswith(f'{file_id}_'):
                            new_path = f'messages/{filename}'
                            self.stdout.write(f'Found matching file: {new_path}')
                            message.media = new_path
                            message.save(update_fields=['media'])
                            fixed_count += 1
                            found = True
                            break
                    
                    if not found:
                        self.stdout.write(self.style.WARNING(f'Could not find media file for message {message.id}, path: {current_path}'))
                        # Clear invalid media reference
                        message.media = ''
                        message.save(update_fields=['media'])
                        errors_count += 1
                        
            except Exception as e:
                self.stdout.write(self.style.ERROR(f'Error processing message {message.id}: {str(e)}'))
                errors_count += 1
        
        self.stdout.write(self.style.SUCCESS(f'Media path fix completed! Fixed {fixed_count} messages, {errors_count} errors.'))