#!/usr/bin/env python3
"""
Standalone health check script that can be run directly to verify
the application is working properly. This is used by Railway's health check
to determine if the application is healthy.
"""

import sys
import os
import socket
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(levelname)s %(asctime)s %(name)s %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S',
)
logger = logging.getLogger('health')

def check_socket():
    """Check if the server is listening on port 8080"""
    logger.info("Checking if server is listening on port 8080")
    
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.settimeout(5)
    
    try:
        sock.connect(('127.0.0.1', 8080))
        sock.close()
        logger.info("Server is listening on port 8080")
        return True
    except Exception as e:
        logger.error(f"Socket connection failed: {e}")
        return False

def create_health_file():
    """Create a health check file in the staticfiles directory"""
    logger.info("Creating health check file")
    
    os.makedirs('staticfiles', exist_ok=True)
    
    with open('staticfiles/health.html', 'w') as f:
        f.write('OK')
    
    with open('health.txt', 'w') as f:
        f.write('OK')
    
    logger.info("Health check files created")

if __name__ == "__main__":
    logger.info("Running standalone health check")
    
    # Create health check files
    create_health_file()
    
    # Check if server is listening
    if check_socket():
        logger.info("Health check passed")
        sys.exit(0)
    else:
        logger.error("Health check failed")
        sys.exit(1) 