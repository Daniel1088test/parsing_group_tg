#!/usr/bin/env python3
"""
Script to deploy to Railway with template fixes
"""
import os
import sys
import subprocess
import logging

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('deploy_to_railway.log')
    ]
)
logger = logging.getLogger('deploy_railway')

def run_command(command):
    """Run a command and log output"""
    logger.info(f"Running: {command}")
    process = subprocess.Popen(
        command,
        shell=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        universal_newlines=True
    )
    
    # Read and log output in real-time
    output = []
    for line in iter(process.stdout.readline, ''):
        line = line.strip()
        logger.info(line)
        output.append(line)
        if not line:
            break
    
    # Wait for the process to complete
    process.wait()
    
    return {
        'returncode': process.returncode,
        'output': '\n'.join(output)
    }

def main():
    """Main deployment function"""
    logger.info("Starting Railway deployment")
    
    # Ensure our template fix scripts exist
    if not os.path.exists('fix_railway_templates.py'):
        logger.error("fix_railway_templates.py not found!")
        return False
    
    # Ensure index.html exists at root
    if not os.path.exists('index.html'):
        logger.error("index.html not found at root!")
        return False
    
    # Check if Railway CLI is installed
    result = run_command("railway --version")
    if result['returncode'] != 0:
        logger.error("Railway CLI not installed or not found in PATH")
        return False
    
    # Deploy to Railway
    logger.info("Deploying to Railway...")
    
    # First, link to the project
    run_command("railway link")
    
    # Deploy the changes
    deploy_result = run_command("railway up")
    
    if deploy_result['returncode'] == 0:
        logger.info("Successfully deployed to Railway!")
        # Get the URL of the deployed app
        url_result = run_command("railway status")
        if "up.railway.app" in url_result['output']:
            import re
            match = re.search(r'(https://[a-zA-Z0-9-]+\.up\.railway\.app)', url_result['output'])
            if match:
                url = match.group(1)
                logger.info(f"Deployed app URL: {url}")
        return True
    else:
        logger.error("Failed to deploy to Railway")
        return False

if __name__ == "__main__":
    try:
        success = main()
        if success:
            logger.info("Deployment completed successfully")
            sys.exit(0)
        else:
            logger.error("Deployment failed")
            sys.exit(1)
    except Exception as e:
        logger.error(f"Unhandled error: {e}")
        sys.exit(1) 