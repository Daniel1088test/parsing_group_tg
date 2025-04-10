#!/usr/bin/env python3
import os
import sys
import logging
import subprocess
import importlib

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(levelname)s %(asctime)s %(name)s %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S',
)
logger = logging.getLogger('restart_server')

def clean_pyc_files():
    """Remove all .pyc files to ensure clean imports"""
    logger.info("Cleaning Python cache files")
    
    root_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    count = 0
    
    for dirpath, dirnames, filenames in os.walk(root_dir):
        for filename in filenames:
            if filename.endswith('.pyc') or filename.endswith('.pyo'):
                filepath = os.path.join(dirpath, filename)
                try:
                    os.remove(filepath)
                    count += 1
                    logger.info(f"Removed cache file: {filepath}")
                except Exception as e:
                    logger.error(f"Error removing {filepath}: {e}")
                    
    # Also remove __pycache__ directories
    for dirpath, dirnames, filenames in os.walk(root_dir):
        for dirname in dirnames:
            if dirname == '__pycache__':
                cache_dir = os.path.join(dirpath, dirname)
                try:
                    for f in os.listdir(cache_dir):
                        os.remove(os.path.join(cache_dir, f))
                    os.rmdir(cache_dir)
                    logger.info(f"Removed cache directory: {cache_dir}")
                except Exception as e:
                    logger.error(f"Error removing {cache_dir}: {e}")
    
    logger.info(f"Removed {count} cache files")
    return count

def reload_modules():
    """Force reload of key modules"""
    logger.info("Reloading key modules")
    
    modules_to_reload = [
        'admin_panel.views',
        'admin_panel.urls',
    ]
    
    for module_name in modules_to_reload:
        try:
            if module_name in sys.modules:
                logger.info(f"Reloading module: {module_name}")
                importlib.reload(sys.modules[module_name])
        except Exception as e:
            logger.error(f"Error reloading {module_name}: {e}")

def verify_view_exists():
    """Verify that the run_migrations_view exists in the views module"""
    try:
        import admin_panel.views
        if hasattr(admin_panel.views, 'run_migrations_view'):
            logger.info("run_migrations_view function exists in views module")
            return True
        else:
            logger.error("run_migrations_view function NOT found in views module")
            return False
    except Exception as e:
        logger.error(f"Error importing views module: {e}")
        return False

if __name__ == "__main__":
    logger.info("Starting server restart process")
    
    # Clean Python cache files
    clean_pyc_files()
    
    # Reload modules
    reload_modules()
    
    # Verify the view exists
    if verify_view_exists():
        logger.info("View verification successful")
    else:
        logger.warning("View verification failed - check your code")
    
    logger.info("Restart process completed")
    logger.info("Please restart your application server now") 