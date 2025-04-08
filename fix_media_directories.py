#!/usr/bin/env python
"""
Emergency fix for media directories in Railway deployment.
This script will fix any issues with circular symlinks and ensure the proper directory structure.
Run this before starting the application.
"""

import os
import sys
import logging
import shutil

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S',
)
logger = logging.getLogger('fix_media_directories')

def fix_media_directories():
    """
    Fix any issues with media directories and symlinks.
    """
    # Define known problematic paths
    problematic_paths = [
        "/app/media/messages",
        "/app/media",
        "/app/staticfiles/media"
    ]
    
    # First, remove any problematic symlinks or empty directories
    for path in problematic_paths:
        try:
            if os.path.islink(path):
                # It's a symlink, remove it
                target = os.readlink(path)
                logger.info(f"Removing problematic symlink: {path} -> {target}")
                os.unlink(path)
            elif os.path.isdir(path) and not os.listdir(path):
                # It's an empty directory, remove it
                logger.info(f"Removing empty directory: {path}")
                os.rmdir(path)
            elif os.path.isdir(path):
                # It's a non-empty directory, keep it
                logger.info(f"Found non-empty directory: {path}")
            elif os.path.exists(path):
                # It's something else (file?), remove it
                logger.info(f"Removing unexpected file: {path}")
                os.remove(path)
            else:
                logger.info(f"Path does not exist: {path}")
        except Exception as e:
            logger.warning(f"Error processing path {path}: {e}")
    
    # Create real directories
    real_dirs = [
        "/app/media",
        "/app/media/messages",
        "/app/staticfiles",
        "/app/staticfiles/img"
    ]
    
    for dir_path in real_dirs:
        try:
            if not os.path.exists(dir_path):
                os.makedirs(dir_path, exist_ok=True)
                logger.info(f"Created directory: {dir_path}")
            
            # Set permissions
            os.chmod(dir_path, 0o755)
            logger.info(f"Set permissions for: {dir_path}")
        except Exception as e:
            logger.error(f"Error creating directory {dir_path}: {e}")
    
    # Create test files to verify write permissions
    for dir_path in ["/app/media/messages", "/app/staticfiles/img"]:
        try:
            test_file = os.path.join(dir_path, ".write_test")
            with open(test_file, 'w') as f:
                f.write("test")
            logger.info(f"Successfully wrote test file in {dir_path}")
            os.remove(test_file)
        except Exception as e:
            logger.error(f"Cannot write to directory {dir_path}: {e}")
    
    logger.info("Media directory structure fixed successfully")

if __name__ == "__main__":
    try:
        logger.info("Starting emergency media directory fix")
        fix_media_directories()
        logger.info("Media directories fixed. Application can start normally.")
        sys.exit(0)
    except Exception as e:
        logger.error(f"Error during media fix: {e}")
        sys.exit(1) 