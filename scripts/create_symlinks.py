#!/usr/bin/env python
"""
Script for creating symbolic links for media access on Railway deployment.
This script properly configures Django settings before execution.
"""
import os
import sys
import django

# Configure Django settings
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()

# Now we can import Django settings and models
from django.conf import settings
import logging

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(levelname)s %(asctime)s %(name)s %(process)d %(thread)d %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S',
)
logger = logging.getLogger('create_symlinks')

def main():
    """Main function to create symbolic links for media files"""
    try:
        logger.info("Starting symlink creation...")
        
        # Print environment information
        logger.info(f"MEDIA_ROOT: {settings.MEDIA_ROOT}")
        logger.info(f"STATIC_ROOT: {settings.STATIC_ROOT}")
        
        # Create symbolic link from /app/staticfiles/media to /app/media
        static_media_path = os.path.join(settings.STATIC_ROOT, 'media')
        
        # Remove the existing symlink if it exists
        if os.path.islink(static_media_path):
            os.unlink(static_media_path)
            logger.info(f"Removed existing symlink: {static_media_path}")
        
        # Create the symbolic link
        try:
            os.symlink(settings.MEDIA_ROOT, static_media_path)
            logger.info(f"Created symlink: {static_media_path} -> {settings.MEDIA_ROOT}")
        except FileExistsError:
            logger.warning(f"Symlink already exists: {static_media_path}")
        except Exception as e:
            logger.error(f"Error creating symlink: {e}")
        
        logger.info("Symlink creation completed successfully!")
        return 0
    except Exception as e:
        logger.error(f"Error in create_symlinks script: {e}", exc_info=True)
        return 1

if __name__ == "__main__":
    sys.exit(main()) 