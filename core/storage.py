"""
Custom storage handlers for Railway's ephemeral filesystem
"""

import os
import logging
from django.conf import settings
from django.core.files.storage import FileSystemStorage

logger = logging.getLogger('railway_storage')

class RailwayMediaStorage(FileSystemStorage):
    """
    Custom storage backend for Railway that handles ephemeral filesystem issues
    """
    
    def __init__(self, *args, **kwargs):
        """Initialize with default media location"""
        location = getattr(settings, 'MEDIA_ROOT', None)
        super().__init__(location=location, *args, **kwargs)
        
        # Ensure the media directories exist
        self._ensure_directories_exist()
    
    def _ensure_directories_exist(self):
        """Make sure all necessary directories exist"""
        try:
            # Create main media directory
            os.makedirs(self.location, exist_ok=True)
            
            # Create messages directory for telegram media
            messages_dir = os.path.join(self.location, 'messages')
            os.makedirs(messages_dir, exist_ok=True)
            
            logger.info(f"Ensured media directories exist: {self.location}")
        except Exception as e:
            logger.error(f"Error creating media directories: {e}")
    
    def url(self, name):
        """Return URL for the file, with fallback for missing files"""
        return f"{settings.MEDIA_URL}{name}"
    
    def exists(self, name):
        """Check if file exists, with logging for missing files"""
        exists = super().exists(name)
        if not exists:
            logger.warning(f"Media file doesn't exist: {name}")
        return exists

# Helper function to initialize storage
def init_railway_storage():
    """Initialize the Railway storage system"""
    storage = RailwayMediaStorage()
    logger.info("Railway media storage initialized")
    return storage