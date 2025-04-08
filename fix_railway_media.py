#!/usr/bin/env python
"""
Standalone script to fix media file permissions and missing files on Railway deployments.
This script can be run directly on the Railway instance to repair media issues.
"""

import os
import sys
import django
import logging
import shutil
import mimetypes
from pathlib import Path
from django.db import models

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S',
)
logger = logging.getLogger('fix_railway_media')

# Setup Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()

from django.conf import settings
from admin_panel.models import Message

def create_directory_structure():
    """Create all necessary directories with correct permissions"""
    logger.info("Creating directory structure...")
    
    # Define essential directories
    directories = [
        settings.MEDIA_ROOT,
        os.path.join(settings.MEDIA_ROOT, 'messages'),
        settings.STATIC_ROOT,
        os.path.join(settings.STATIC_ROOT, 'img'),
        'data/sessions',
    ]
    
    # Create each directory with proper permissions
    for directory in directories:
        try:
            # Check if directory exists before creating
            if not os.path.exists(directory):
                os.makedirs(directory, exist_ok=True)
                logger.info(f"Created directory: {directory}")
            else:
                logger.info(f"Directory already exists: {directory}")
            
            # Set directory permissions
            try:
                os.chmod(directory, 0o755)
                logger.info(f"Set directory permissions for: {directory}")
            except Exception as e:
                logger.warning(f"Could not set permissions for directory {directory}: {e}")
        except Exception as e:
            # Only log as error if it's not the "File exists" error
            if "File exists" not in str(e):
                logger.error(f"Error creating directory {directory}: {e}")
            else:
                logger.info(f"Directory already exists (from error): {directory}")

def create_placeholder_images():
    """Create placeholder images for missing media files"""
    logger.info("Creating placeholder images...")
    
    try:
        from PIL import Image, ImageDraw
        
        # Define placeholder paths
        placeholders = [
            (os.path.join(settings.STATIC_ROOT, 'img', 'placeholder-image.png'), "IMAGE"),
            (os.path.join(settings.STATIC_ROOT, 'img', 'placeholder-video.png'), "VIDEO"),
        ]
        
        # Create each placeholder
        for path, text in placeholders:
            if not os.path.exists(path):
                logger.info(f"Creating placeholder: {path}")
                
                # Create the image
                img = Image.new('RGB', (300, 200), color=(240, 240, 240))
                draw = ImageDraw.Draw(img)
                draw.rectangle([(0, 0), (299, 199)], outline=(200, 200, 200), width=2)
                draw.text((150, 100), text, fill=(100, 100, 100))
                img.save(path)
                
                # Set file permissions
                try:
                    os.chmod(path, 0o644)
                    logger.info(f"Set file permissions for: {path}")
                except Exception as e:
                    logger.warning(f"Could not set permissions for {path}: {e}")
            else:
                logger.info(f"Placeholder already exists: {path}")
                
                # Ensure file permissions are correct
                try:
                    os.chmod(path, 0o644)
                except Exception as e:
                    logger.warning(f"Could not set permissions for existing placeholder {path}: {e}")
    except ImportError:
        logger.error("PIL (Pillow) library not available. Cannot create image placeholders.")

def fix_media_files():
    """Fix all media files in the database"""
    logger.info("Fixing media files...")
    
    # Get placeholders
    image_placeholder = os.path.join(settings.STATIC_ROOT, 'img', 'placeholder-image.png')
    video_placeholder = os.path.join(settings.STATIC_ROOT, 'img', 'placeholder-video.png')
    
    # Make sure placeholders exist - recreate them if they don't
    create_placeholder_images()
    
    # Get all messages with media type set
    try:
        # Get all messages with either media or original_url
        messages = Message.objects.filter(
            (models.Q(media__isnull=False) & ~models.Q(media='')) |
            (models.Q(original_url__isnull=False) & ~models.Q(original_url=''))
        )
        logger.info(f"Found {len(messages)} messages with media")
        
        fixed_count = 0
        for message in messages:
            try:
                # Process messages with media path
                if message.media:
                    media_path_str = str(message.media)
                    if not media_path_str.startswith('messages/'):
                        media_path_str = f"messages/{media_path_str}"
                        
                    media_path = os.path.join(settings.MEDIA_ROOT, media_path_str)
                    logger.info(f"Processing: {media_path}")
                    
                    # Check if file exists
                    if not os.path.exists(media_path):
                        logger.warning(f"File does not exist: {media_path}")
                        
                        # If we have an original URL, we can clear the media path and keep the media_type
                        if message.original_url:
                            logger.info(f"Message has original URL: {message.original_url}")
                            message.media = ""
                            message.save(update_fields=['media'])
                            fixed_count += 1
                            continue
                        
                        # Determine which placeholder to use
                        if message.media_type in ['photo', 'image', 'gif']:
                            placeholder = image_placeholder
                            content_type = 'image/jpeg'
                        else:
                            placeholder = video_placeholder
                            content_type = 'video/mp4'
                        
                        # Create directory if needed
                        media_dir = os.path.dirname(media_path)
                        if not os.path.exists(media_dir):
                            try:
                                os.makedirs(media_dir, exist_ok=True)
                                os.chmod(media_dir, 0o755)
                                logger.info(f"Created directory: {media_dir}")
                            except Exception as e:
                                logger.error(f"Error creating directory {media_dir}: {e}")
                                continue
                        
                        # Copy placeholder
                        try:
                            shutil.copy2(placeholder, media_path)
                            os.chmod(media_path, 0o644)
                            logger.info(f"Created placeholder for {media_path_str}")
                            fixed_count += 1
                        except Exception as e:
                            logger.error(f"Error creating placeholder for {media_path_str}: {e}")
                    else:
                        # File exists, ensure permissions
                        logger.info(f"File exists: {media_path}")
                        try:
                            os.chmod(media_path, 0o644)
                            logger.info(f"Updated permissions for: {media_path}")
                        except Exception as e:
                            logger.warning(f"Could not set permissions for {media_path}: {e}")
                            
                # Handle messages with original_url but no media
                elif message.original_url and not message.media and message.media_type:
                    logger.info(f"Message has original URL but no media: {message.original_url}")
                    # This is actually okay, we'll display using the original URL
                    pass
            except Exception as e:
                logger.error(f"Error processing message {message.id}: {e}")
                    
        logger.info(f"Fixed {fixed_count} missing media files")
    except Exception as e:
        logger.error(f"Error fixing media files: {e}")
        
    # Print a summary of the media situation
    try:
        total_messages = Message.objects.count()
        media_messages = Message.objects.exclude(media_type__isnull=True).exclude(media_type='').count()
        media_with_file = Message.objects.exclude(media__isnull=True).exclude(media='').count()
        media_with_url = Message.objects.exclude(original_url__isnull=True).exclude(original_url='').count()
        
        logger.info(f"Media summary:")
        logger.info(f"Total messages: {total_messages}")
        logger.info(f"Messages with media_type: {media_messages}")
        logger.info(f"Messages with media file: {media_with_file}")
        logger.info(f"Messages with original URL: {media_with_url}")
    except Exception as e:
        logger.error(f"Error generating media summary: {e}")

def create_symlinks():
    """Create necessary symlinks for consistent media access"""
    logger.info("Creating symlinks for consistent media access...")
    
    # First, check for and remove any existing problematic symlinks
    problematic_paths = [
        "/app/media/messages",
        os.path.join(settings.MEDIA_ROOT, "messages")
    ]
    
    for path in problematic_paths:
        try:
            # Check if it's a symlink, remove it
            if os.path.islink(path):
                logger.info(f"Removing existing symlink: {path}")
                os.unlink(path)
            # If it's a directory but empty, remove it
            elif os.path.isdir(path) and not os.listdir(path):
                logger.info(f"Removing empty directory: {path}")
                os.rmdir(path)
        except Exception as e:
            logger.warning(f"Could not remove path {path}: {e}")
    
    # Ensure we have a real directory for media files
    real_media_dir = os.path.join(settings.MEDIA_ROOT, "messages")
    if not os.path.exists(real_media_dir) or os.path.islink(real_media_dir):
        try:
            # If it's a symlink, remove it first
            if os.path.islink(real_media_dir):
                os.unlink(real_media_dir)
                
            # Create a real directory
            os.makedirs(real_media_dir, exist_ok=True)
            os.chmod(real_media_dir, 0o755)
            logger.info(f"Created real media directory: {real_media_dir}")
        except Exception as e:
            logger.error(f"Error creating real media directory: {e}")
    
    # Create symlink only if the target directory exists and source path doesn't
    if os.path.isdir("/app") and not os.path.exists("/app/media"):
        try:
            # Create the parent directory if needed
            os.makedirs("/app/media", exist_ok=True)
            logger.info("Created /app/media directory")
        except Exception as e:
            logger.error(f"Error creating /app/media: {e}")
    
    logger.info("Media directories and symlinks fixed.")

def main():
    """Main function to run all media fixing operations"""
    logger.info("Starting media fixing operations...")
    
    # Print environment information
    logger.info(f"MEDIA_ROOT: {settings.MEDIA_ROOT}")
    logger.info(f"STATIC_ROOT: {settings.STATIC_ROOT}")
    
    # Run all fixing operations
    create_directory_structure()
    create_placeholder_images()
    fix_media_files()
    create_symlinks()
    
    logger.info("Media fixing operations completed successfully!")

if __name__ == "__main__":
    main()