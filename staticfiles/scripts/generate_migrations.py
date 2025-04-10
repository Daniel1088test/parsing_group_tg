#!/usr/bin/env python3
"""
Script to generate missing migrations for models with changes.
"""

import os
import sys
import logging
import subprocess

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(levelname)s %(asctime)s %(name)s %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S',
)
logger = logging.getLogger('generate_migrations')

def generate_migrations():
    """Generate missing migrations for all apps"""
    logger.info("Generating missing migrations")
    
    # First let's check which apps have model changes
    try:
        result = subprocess.run(
            ["python", "manage.py", "makemigrations", "--dry-run"],
            capture_output=True,
            text=True
        )
        
        if "No changes detected" in result.stdout:
            logger.info("No model changes detected - no migrations needed")
            return True
        else:
            logger.info(f"Changes detected: {result.stdout}")
            
            # Get list of apps with changes
            apps = []
            if "admin_panel" in result.stdout:
                apps.append("admin_panel")
            
            # Generate migrations for each app
            for app in apps:
                logger.info(f"Generating migrations for {app}")
                migration_result = subprocess.run(
                    ["python", "manage.py", "makemigrations", app],
                    capture_output=True,
                    text=True
                )
                
                if migration_result.returncode == 0:
                    logger.info(f"Successfully generated migrations for {app}: {migration_result.stdout}")
                else:
                    logger.error(f"Failed to generate migrations for {app}: {migration_result.stderr}")
            
            # Now apply the generated migrations
            logger.info("Applying generated migrations")
            apply_result = subprocess.run(
                ["python", "manage.py", "migrate"],
                capture_output=True,
                text=True
            )
            
            if apply_result.returncode == 0:
                logger.info(f"Successfully applied migrations: {apply_result.stdout}")
                return True
            else:
                logger.error(f"Failed to apply migrations: {apply_result.stderr}")
                return False
    except Exception as e:
        logger.error(f"Error generating migrations: {e}")
        return False

if __name__ == "__main__":
    logger.info("Starting migration generation script")
    
    if generate_migrations():
        logger.info("Migration generation completed successfully")
        sys.exit(0)
    else:
        logger.error("Migration generation failed")
        sys.exit(1) 