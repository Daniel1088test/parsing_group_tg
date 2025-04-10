#!/usr/bin/env python3
"""
Script to create a restart trigger for Railway deployment
This script creates a file that Railway will use to detect changes and restart the app
"""
import os
import time
import datetime
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('restart-railway')

def main():
    """Create a restart trigger file for Railway"""
    logger.info("=== Railway Restart Trigger ===")
    
    # Create restart trigger file
    restart_file = 'railway_restart_trigger.txt'
    timestamp = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    
    with open(restart_file, 'w') as f:
        f.write(f"Restart triggered at {timestamp}\n")
    
    logger.info(f"Created restart trigger file: {restart_file}")
    
    # Create or update health check files
    health_files = ['health.html', 'healthz.html', 'health.txt', 'healthz.txt']
    for file in health_files:
        with open(file, 'w') as f:
            f.write('OK')
        logger.info(f"Updated health file: {file}")
    
    # Update wsgi.py timestamp to trigger code reload
    try:
        wsgi_file = os.path.join('core', 'wsgi.py')
        if os.path.exists(wsgi_file):
            # Touch the file to update timestamp
            with open(wsgi_file, 'a') as f:
                f.write('\n# Restart trigger: ' + timestamp + '\n')
            logger.info(f"Updated {wsgi_file} timestamp")
    except Exception as e:
        logger.error(f"Error updating wsgi.py: {e}")
    
    logger.info("Restart trigger complete. Railway should detect changes and restart.")
    return True

if __name__ == "__main__":
    main() 