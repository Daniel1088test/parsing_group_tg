#!/usr/bin/env python3
"""
Script to directly check the health endpoint and verify it's working properly.
This helps debugging health check issues with Railway.
"""

import os
import sys
import time
import http.client
import logging
import subprocess
import signal

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(levelname)s %(asctime)s %(name)s %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S',
)
logger = logging.getLogger('health_check')

def verify_health_endpoint():
    """Start a test server and verify the health endpoint is working"""
    logger.info("Starting test server to verify health endpoint")
    
    # Start the server in the background
    server_process = subprocess.Popen(
        ["python", "manage.py", "runserver", "0.0.0.0:8765"],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE
    )
    
    try:
        # Wait for server to start
        logger.info(f"Started server on PID {server_process.pid}")
        logger.info("Waiting 5 seconds for server to initialize...")
        time.sleep(5)
        
        # Try different health check paths
        health_paths = ["/health", "/health/", "/healthz", "/healthz/"]
        success = False
        
        for path in health_paths:
            logger.info(f"Testing health endpoint: {path}")
            try:
                # Try to connect to the server
                conn = http.client.HTTPConnection("127.0.0.1", 8765)
                conn.request("GET", path)
                response = conn.getresponse()
                
                status = response.status
                body = response.read().decode('utf-8')
                
                logger.info(f"Status: {status}, Body: {body}")
                
                if status == 200 and body == "OK":
                    logger.info(f"Health check passed for {path}!")
                    success = True
                else:
                    logger.warning(f"Health check responded but with unexpected result for {path}")
            except Exception as e:
                logger.error(f"Error checking {path}: {e}")
        
        return success
    finally:
        # Clean up the server process
        logger.info("Terminating test server")
        server_process.terminate()
        try:
            server_process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            logger.warning("Server didn't terminate gracefully, killing it")
            server_process.kill()

def create_health_files():
    """Create static health check files in various locations"""
    logger.info("Creating static health check files")
    
    # Ensure directories exist
    os.makedirs("staticfiles", exist_ok=True)
    os.makedirs("static", exist_ok=True)
    
    # Create health check files
    health_files = [
        "staticfiles/health.html",
        "staticfiles/healthz.html",
        "static/health.html",
        "static/healthz.html",
        "health.html",
        "healthz.html"
    ]
    
    for file_path in health_files:
        try:
            with open(file_path, "w") as f:
                f.write("OK")
            logger.info(f"Created health file: {file_path}")
        except Exception as e:
            logger.error(f"Error creating {file_path}: {e}")

if __name__ == "__main__":
    logger.info("Starting health check verification")
    
    # Create static health files
    create_health_files()
    
    # Verify the health endpoint
    if verify_health_endpoint():
        logger.info("Health check verification successful")
        sys.exit(0)
    else:
        logger.error("Health check verification failed")
        sys.exit(1) 