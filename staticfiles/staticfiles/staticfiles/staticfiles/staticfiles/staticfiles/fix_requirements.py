#!/usr/bin/env python
"""
Simple script to fix requirements.txt issues
"""
import os
import sys
import logging

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger("fix_requirements")

def fix_requirements():
    """Ensure all requirements files exist and have the necessary dependencies"""
    logger.info("Checking requirements files...")
    
    # Paths to check
    base_req = "requirements-base.txt"
    full_req = "requirements.txt"
    
    # Essential packages that must be present
    essential_packages = [
        "django==4.2.7",
        "psycopg2-binary==2.9.9",
        "python-telegram-bot==20.4",
        "telethon==1.33.1",
        "asyncio==3.4.3",
        "psutil==5.9.6",
        "pillow==10.1.0",
        "gunicorn==20.1.0"
    ]
    
    # Check if base requirements file exists, create if not
    if not os.path.exists(base_req):
        logger.info(f"Creating {base_req}")
        with open(base_req, 'w') as f:
            f.write("\n".join(essential_packages))
    
    # Check if main requirements file exists, create if not
    if not os.path.exists(full_req):
        logger.info(f"Creating {full_req}")
        with open(full_req, 'w') as f:
            f.write("\n".join(essential_packages))
    
    # Check contents of base requirements and add missing essentials
    with open(base_req, 'r') as f:
        base_content = f.read()
    
    missing = []
    for package in essential_packages:
        package_name = package.split("==")[0]
        if package_name not in base_content:
            missing.append(package)
    
    if missing:
        logger.info(f"Adding missing essential packages to {base_req}")
        with open(base_req, 'a') as f:
            f.write("\n" + "\n".join(missing))
    
    logger.info("Requirements files checked and fixed")
    return True

if __name__ == "__main__":
    try:
        fix_requirements()
        sys.exit(0)
    except Exception as e:
        logger.error(f"Error fixing requirements: {e}")
        sys.exit(1) 