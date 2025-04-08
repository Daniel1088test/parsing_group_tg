#!/usr/bin/env python3
import os
import sys
import logging
import django
import shutil

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(levelname)s %(asctime)s %(filename)s %(lineno)d %(process)d %(message)s',
)
logger = logging.getLogger(__name__)

try:
    # Try to set up Django
    logger.info("Attempting to set up Django for symlink creation...")
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "core.settings")
    django.setup()
    
    # Import after Django setup
    try:
        from django.conf import settings
        
        # Create symlinks using Django settings
        logger.info("Creating symlinks using Django settings...")
        
        # Define source and target directories
        media_root = settings.MEDIA_ROOT
        static_root = settings.STATIC_ROOT
        
        # Create symlink from static to media if needed
        media_symlink = os.path.join(static_root, 'media')
        
        if not os.path.exists(media_symlink):
            try:
                os.symlink(media_root, media_symlink)
                logger.info(f"Created symlink: {media_symlink} -> {media_root}")
            except OSError:
                # Fallback for platforms that don't support symlinks
                logger.warning(f"Symlink creation failed, creating directory: {media_symlink}")
                os.makedirs(media_symlink, exist_ok=True)
        else:
            logger.info(f"Symlink already exists: {media_symlink}")
            
        logger.info("Symlink creation complete")
        
    except ImportError as e:
        logger.warning(f"Could not import Django settings: {str(e)}")
        logger.info("Continuing without settings access")

except (ImportError, ModuleNotFoundError) as e:
    # Handle missing Django or core module
    logger.warning(f"Django setup failed: {str(e)}")
    logger.info("Creating directories and placeholders as fallback...")
    
    # Create standard directories
    dirs_to_create = [
        "media",
        "media/messages",
        "staticfiles",
        "staticfiles/img",
        "staticfiles/media"
    ]
    
    for directory in dirs_to_create:
        try:
            os.makedirs(directory, exist_ok=True)
            logger.info(f"Created directory: {directory}")
        except Exception as e:
            logger.error(f"Failed to create directory {directory}: {str(e)}")
    
    # Create a basic .htaccess file for media redirection
    htaccess_path = os.path.join("staticfiles", "media", ".htaccess")
    try:
        with open(htaccess_path, "w") as f:
            f.write("""
# Redirect media requests to the media directory
<IfModule mod_rewrite.c>
    RewriteEngine On
    RewriteRule ^(.*)$ /media/$1 [L]
</IfModule>
""")
        logger.info(f"Created .htaccess file: {htaccess_path}")
    except Exception as e:
        logger.error(f"Failed to create .htaccess file: {str(e)}")
    
    # Copy placeholder images to the media directory
    placeholder_image = os.path.join("staticfiles", "img", "placeholder-image.png")
    placeholder_video = os.path.join("staticfiles", "img", "placeholder-video.png")
    
    # Check if placeholders exist, if not create them
    for placeholder in [placeholder_image, placeholder_video]:
        if not os.path.exists(placeholder):
            try:
                # Create a simple placeholder (1x1 pixel)
                with open(placeholder, "wb") as f:
                    # Simple 1x1 transparent PNG
                    f.write(b'\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x06\x00\x00\x00\x1f\x15\xc4\x89\x00\x00\x00\nIDATx\x9cc\x00\x01\x00\x00\x05\x00\x01\r\n-\xb4\x00\x00\x00\x00IEND\xaeB`\x82')
                logger.info(f"Created placeholder: {placeholder}")
            except Exception as e:
                logger.error(f"Failed to create placeholder: {str(e)}")
        
        # Copy to media directory
        try:
            media_placeholder = os.path.join("staticfiles", "media", os.path.basename(placeholder))
            shutil.copy2(placeholder, media_placeholder)
            logger.info(f"Copied placeholder to media directory: {media_placeholder}")
        except Exception as e:
            logger.error(f"Failed to copy placeholder: {str(e)}")

    logger.info("Symlink/directory creation completed in fallback mode")

# Always exit cleanly
logger.info("Script execution complete") 