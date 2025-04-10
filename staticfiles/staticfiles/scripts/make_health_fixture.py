#!/usr/bin/env python3
"""
Script to create and verify health endpoint files for Railway deployments.
This is a standalone script that doesn't rely on Django imports.
"""

import os
import sys
import logging
import http.client
import time
import socket
import subprocess

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(levelname)s %(asctime)s %(name)s %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S',
)
logger = logging.getLogger('health_fixture')

def create_health_files():
    """Create health check files in all relevant directories"""
    logger.info("Creating health check files")
    
    # Create required directories
    os.makedirs('staticfiles', exist_ok=True)
    os.makedirs('static', exist_ok=True)
    
    # Content for HTML files
    html_content = "<!DOCTYPE html><html><body>OK</body></html>"
    
    # Content for plain text files
    text_content = "OK"
    
    # Files to create
    files = [
        # HTML files
        ('staticfiles/health.html', html_content),
        ('staticfiles/healthz.html', html_content),
        ('static/health.html', html_content),
        ('static/healthz.html', html_content),
        
        # Plain text files
        ('staticfiles/health.txt', text_content),
        ('staticfiles/healthz.txt', text_content),
        ('health.txt', text_content),
        ('healthz.txt', text_content),
        
        # Root level files
        ('health.html', html_content),
        ('healthz.html', html_content),
    ]
    
    # Create each file
    for file_path, content in files:
        try:
            with open(file_path, 'w') as f:
                f.write(content)
            logger.info(f"Created health file: {file_path}")
            # Set permissions
            try:
                os.chmod(file_path, 0o644)
            except:
                pass
        except Exception as e:
            logger.error(f"Error creating {file_path}: {e}")
    
    # Ensure healthcheck.txt is in the proper format
    try:
        with open('healthcheck.txt', 'w') as f:
            f.write("/health\n200 OK\n")
        logger.info("Created proper healthcheck.txt file")
    except Exception as e:
        logger.error(f"Error creating healthcheck.txt: {e}")

def check_port_availability(port):
    """Check if a port is available"""
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.bind(('0.0.0.0', port))
        s.close()
        return True
    except:
        return False

def test_health_endpoint():
    """Start a test server and check if health endpoint works"""
    logger.info("Testing health endpoint")
    
    # Find an available port
    test_port = 8765
    while not check_port_availability(test_port) and test_port < 9000:
        test_port += 1
    
    if test_port >= 9000:
        logger.error("Could not find an available port")
        return False
    
    logger.info(f"Using port {test_port} for test server")
    
    # Start a local server on the test port
    server_process = subprocess.Popen(
        ["python", "manage.py", "runserver", f"0.0.0.0:{test_port}"],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL
    )
    
    try:
        # Wait for server to start
        logger.info("Waiting for server to start...")
        time.sleep(5)
        
        # Test health endpoints
        endpoints = ['/health', '/health/', '/healthz', '/healthz/', '/health.html', '/healthz.html']
        success = False
        
        for endpoint in endpoints:
            try:
                logger.info(f"Testing endpoint: {endpoint}")
                conn = http.client.HTTPConnection('127.0.0.1', test_port)
                conn.request('GET', endpoint)
                response = conn.getresponse()
                
                status = response.status
                body = response.read().decode('utf-8')
                
                logger.info(f"Response status: {status}, body length: {len(body)}")
                
                if status == 200:
                    logger.info(f"Health check passed for {endpoint}")
                    success = True
                else:
                    logger.warning(f"Health check failed for {endpoint}: status {status}")
            except Exception as e:
                logger.error(f"Error testing {endpoint}: {e}")
        
        if success:
            logger.info("At least one health endpoint is working")
        else:
            logger.error("All health endpoints failed")
        
        return success
    finally:
        # Clean up
        logger.info("Stopping test server")
        server_process.terminate()
        try:
            server_process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            server_process.kill()

if __name__ == "__main__":
    logger.info("Starting health fixture setup")
    
    # Create all health files
    create_health_files()
    
    # Test health endpoint if requested
    if len(sys.argv) > 1 and sys.argv[1] == '--test':
        if test_health_endpoint():
            logger.info("Health fixture setup completed successfully with endpoint test")
            sys.exit(0)
        else:
            logger.error("Health fixture setup completed but endpoint test failed")
            sys.exit(1)
    else:
        logger.info("Health fixture setup completed successfully")
        sys.exit(0) 