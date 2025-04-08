#!/usr/bin/env python
"""
Verification script for Telegram Session Authentication System

This script verifies that all components of the Telegram session authentication system
are properly configured and working, both locally and when deployed to Railway.
"""

import os
import sys
import logging
import asyncio
import django
from datetime import datetime

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S',
)
logger = logging.getLogger('verify_auth')

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()

from django.conf import settings
from admin_panel.models import TelegramSession
from tg_bot.auth_telethon import verify_session
from tg_bot.config import API_ID, API_HASH

async def verify_auth_system():
    """Verify the authentication system is working properly"""
    logger.info("Starting authentication system verification...")
    
    # 1. Check environment variables
    logger.info("Checking environment variables...")
    bot_token = os.environ.get('BOT_TOKEN')
    if not bot_token:
        logger.error("BOT_TOKEN environment variable is not set")
    else:
        logger.info("BOT_TOKEN is set ✓")
        
    if not API_ID or not API_HASH:
        logger.error("API_ID or API_HASH not properly configured")
    else:
        logger.info(f"API_ID and API_HASH are configured ✓")
    
    # 2. Check database connection
    logger.info("Checking database connection...")
    try:
        from django.db import connection
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
            result = cursor.fetchone()
            if result and result[0] == 1:
                logger.info("Database connection successful ✓")
            else:
                logger.error("Database query failed")
    except Exception as e:
        logger.error(f"Database connection error: {e}")
    
    # 3. Check TelegramSession model
    logger.info("Checking TelegramSession model...")
    try:
        fields = [f.name for f in TelegramSession._meta.get_fields()]
        required_fields = ['phone', 'api_id', 'api_hash', 'session_file', 'needs_auth', 'auth_token']
        
        missing_fields = [field for field in required_fields if field not in fields]
        if missing_fields:
            logger.error(f"Missing fields in TelegramSession model: {', '.join(missing_fields)}")
        else:
            logger.info("TelegramSession model has all required fields ✓")
    except Exception as e:
        logger.error(f"Error checking TelegramSession model: {e}")
    
    # 4. Check directories
    logger.info("Checking required directories...")
    required_dirs = [
        os.path.join(settings.BASE_DIR, 'data'),
        os.path.join(settings.BASE_DIR, 'data', 'sessions'),
        os.path.join(settings.MEDIA_ROOT),
    ]
    
    for directory in required_dirs:
        if os.path.exists(directory) and os.path.isdir(directory):
            logger.info(f"Directory exists: {directory} ✓")
        else:
            try:
                os.makedirs(directory, exist_ok=True)
                logger.info(f"Created directory: {directory} ✓")
            except Exception as e:
                logger.error(f"Error creating directory {directory}: {e}")
    
    # 5. Check existing sessions
    logger.info("Checking existing sessions...")
    sessions = await get_sessions()
    if not sessions:
        logger.warning("No sessions found in database")
    else:
        logger.info(f"Found {len(sessions)} sessions in database ✓")
        
        # Check session files
        for session in sessions:
            if session['session_file']:
                session_path = session['session_file']
                if os.path.exists(f"{session_path}.session"):
                    is_valid, _ = await verify_session(session_path, API_ID, API_HASH)
                    if is_valid:
                        logger.info(f"Session {session_path} is valid ✓")
                    else:
                        logger.warning(f"Session {session_path} exists but is not valid")
                else:
                    logger.warning(f"Session file not found: {session_path}.session")
    
    # 6. Check authorization views and templates
    logger.info("Checking authorization views and templates...")
    templates_to_check = [
        'admin_panel/authorize_session.html',
        'admin_panel/authorize_session_confirm.html',
        'admin_panel/auth_help.html',
    ]
    
    for template in templates_to_check:
        template_path = os.path.join(settings.BASE_DIR, 'templates', template)
        if os.path.exists(template_path):
            logger.info(f"Template exists: {template} ✓")
        else:
            logger.error(f"Template missing: {template}")
    
    logger.info("Verification complete.")

async def get_sessions():
    """Get all sessions from the database"""
    try:
        return list(TelegramSession.objects.all().values())
    except Exception as e:
        logger.error(f"Error getting sessions: {e}")
        return []

if __name__ == "__main__":
    logger.info(f"=== Authentication System Verification ({datetime.now().strftime('%Y-%m-%d %H:%M:%S')}) ===")
    asyncio.run(verify_auth_system())
    logger.info("=== Verification Complete ===")