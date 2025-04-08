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
            os.makedirs(directory, exist_ok=True)
            logger.info(f"Created/ensured directory: {directory}")
            
            # Set directory permissions
            try:
                os.chmod(directory, 0o755)
                logger.info(f"Set directory permissions for: {directory}")
            except Exception as e:
                logger.warning(f"Could not set permissions for directory {directory}: {e}")
        except Exception as e:
            logger.error(f"Error creating directory {directory}: {e}")

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
    
    # Get all messages with media
    try:
        messages = Message.objects.exclude(media__isnull=True).exclude(media='')
        logger.info(f"Found {len(messages)} messages with media")
        
        fixed_count = 0
        for message in messages:
            if not message.media:
                continue
            
            # Get media path
            media_path_str = str(message.media)
            if not media_path_str.startswith('messages/'):
                media_path_str = f"messages/{media_path_str}"
                
            media_path = os.path.join(settings.MEDIA_ROOT, media_path_str)
            logger.info(f"Processing: {media_path}")
            
            # Check if file exists
            if not os.path.exists(media_path):
                logger.warning(f"File does not exist: {media_path}")
                
                # Determine which placeholder to use
                if message.media_type in ['photo', 'image', 'gif']:
                    placeholder = image_placeholder
                    content_type = 'image/jpeg'
                else:
                    placeholder = video_placeholder
                    content_type = 'video/mp4'
                
                # Create directory if needed
                os.makedirs(os.path.dirname(media_path), exist_ok=True)
                
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
                    
        logger.info(f"Fixed {fixed_count} missing media files")
    except Exception as e:
        logger.error(f"Error fixing media files: {e}")

def create_symlinks():
    """Create necessary symlinks for consistent media access"""
    logger.info("Creating symlinks for consistent media access...")
    
    # Link /app/media/messages to the actual media directory
    app_media_dir = "/app/media/messages"
    target_dir = os.path.join(settings.MEDIA_ROOT, 'messages')
    
    try:
        # Create parent directory if needed
        os.makedirs(os.path.dirname(app_media_dir), exist_ok=True)
        
        # Remove existing link or directory
        if os.path.islink(app_media_dir):
            os.unlink(app_media_dir)
        elif os.path.exists(app_media_dir):
            shutil.rmtree(app_media_dir)
            
        # Create the symlink
        os.symlink(target_dir, app_media_dir)
        logger.info(f"Created symlink: {app_media_dir} -> {target_dir}")
    except Exception as e:
        logger.error(f"Error creating symlink: {e}")

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