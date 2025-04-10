#!/usr/bin/env python3
"""
This script ensures that the scripts directory is a proper Python package.
It creates __init__.py files in key directories to ensure proper module importing.
"""

import os
import sys
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(levelname)s %(asctime)s %(name)s %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S',
)
logger = logging.getLogger('make_package')

def ensure_init_files():
    """Create __init__.py files in important directories"""
    logger.info("Ensuring __init__.py files exist in key directories")
    
    # Get the path to the project root directory
    root_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    
    # Directories that should be Python packages
    dirs_to_fix = [
        os.path.join(root_dir, 'scripts'),
        os.path.join(root_dir, 'admin_panel'),
        os.path.join(root_dir, 'admin_panel', 'migrations'),
    ]
    
    for directory in dirs_to_fix:
        init_file = os.path.join(directory, '__init__.py')
        
        if not os.path.exists(directory):
            logger.warning(f"Directory does not exist: {directory}")
            continue
            
        if not os.path.exists(init_file):
            try:
                with open(init_file, 'w') as f:
                    f.write("# Make directory a proper Python package\n")
                logger.info(f"Created {init_file}")
            except Exception as e:
                logger.error(f"Error creating {init_file}: {e}")
        else:
            logger.info(f"Package file already exists: {init_file}")
    
    # Add scripts directory to Python path if needed
    if root_dir not in sys.path:
        sys.path.insert(0, root_dir)
        logger.info(f"Added {root_dir} to Python path")
    
    logger.info("Package setup complete")
    return True

if __name__ == "__main__":
    logger.info("Starting package setup")
    success = ensure_init_files()
    if success:
        logger.info("Package setup completed successfully")
        sys.exit(0)
    else:
        logger.error("Package setup failed")
        sys.exit(1) 