#!/usr/bin/env python
"""
Script for fixing Telegram sessions and media files on Railway deployment.
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
logger = logging.getLogger('fix_sessions')

def main():
    """Main function to fix sessions and media"""
    try:
        logger.info("Starting session fixing operations...")
        
        # Print environment information
        logger.info(f"MEDIA_ROOT: {settings.MEDIA_ROOT}")
        logger.info(f"STATIC_ROOT: {settings.STATIC_ROOT}")
        
        # Create necessary directories
        media_dirs = [
            settings.MEDIA_ROOT,
            os.path.join(settings.MEDIA_ROOT, 'messages'),
            'data',
            'data/sessions',
        ]
        
        for directory in media_dirs:
            try:
                if not os.path.exists(directory):
                    os.makedirs(directory, exist_ok=True)
                    logger.info(f"Created directory: {directory}")
                else:
                    logger.info(f"Directory already exists: {directory}")
                
                # Set proper permissions
                os.chmod(directory, 0o755)
                logger.info(f"Set permissions for: {directory}")
            except Exception as e:
                logger.warning(f"Error creating/setting permissions for {directory}: {e}")
        
        logger.info("Session fixing operations completed successfully!")
        return 0
    except Exception as e:
        logger.error(f"Error in fix_sessions script: {e}", exc_info=True)
        return 1

if __name__ == "__main__":
    sys.exit(main()) 