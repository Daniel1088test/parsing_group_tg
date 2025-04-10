#!/usr/bin/env python3
"""
Script to add the is_authorized field to TelegramSession model and synchronize its state
"""
import os
import sys
import logging
import traceback
import django
from pathlib import Path

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('fix_session_auth.log', encoding='utf-8'),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

# Initialize Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
try:
    django.setup()
    logger.info("Django initialized successfully")
except Exception as e:
    logger.error(f"Error initializing Django: {e}")
    logger.error(traceback.format_exc())
    sys.exit(1)

def add_is_authorized_field():
    """
    Adds the is_authorized field to the TelegramSession model
    """
    try:
        from django.db import connection
        
        # Check if the field already exists
        with connection.cursor() as cursor:
            cursor.execute("""
                SELECT column_name 
                FROM information_schema.columns 
                WHERE table_name = 'admin_panel_telegramsession' 
                AND column_name = 'is_authorized'
            """)
            field_exists = bool(cursor.fetchone())
            
            if field_exists:
                logger.info("is_authorized field already exists in TelegramSession model")
                return True
            
            # Add the field if it doesn't exist
            cursor.execute("""
                ALTER TABLE admin_panel_telegramsession 
                ADD COLUMN is_authorized BOOLEAN DEFAULT FALSE
            """)
            logger.info("Added is_authorized field to TelegramSession model")
        
        return True
    except Exception as e:
        logger.error(f"Error adding is_authorized field: {e}")
        logger.error(traceback.format_exc())
        return False

def update_session_auth_status():
    """
    Updates the is_authorized field based on needs_auth
    """
    try:
        from admin_panel.models import TelegramSession
        
        # Get all sessions
        sessions = TelegramSession.objects.all()
        logger.info(f"Found {len(sessions)} Telegram sessions")
        
        # Update auth status
        for session in sessions:
            try:
                # Set is_authorized to true if needs_auth is False
                if hasattr(session, 'needs_auth') and not session.needs_auth:
                    if hasattr(session, 'is_authorized'):
                        session.is_authorized = True
                        session.save(update_fields=['is_authorized'])
                        logger.info(f"Updated session {session.phone} to is_authorized=True")
            except Exception as se:
                logger.error(f"Error updating session {session.phone}: {se}")
        
        # Check for session files to authorize sessions
        for session in sessions:
            if not (hasattr(session, 'is_authorized') and session.is_authorized):
                # Check if session file exists
                try:
                    session_name = session.session_file or f"telethon_session_{session.phone.replace('+', '')}"
                    session_paths = [
                        f"{session_name}.session",
                        f"data/sessions/{session_name}.session",
                        os.path.join("data", "sessions", f"{session_name}.session")
                    ]
                    
                    file_found = False
                    for path in session_paths:
                        if os.path.exists(path):
                            file_found = True
                            logger.info(f"Found session file for {session.phone} at {path}")
                            break
                    
                    if file_found:
                        session.is_authorized = True
                        session.needs_auth = False
                        session.save(update_fields=['is_authorized', 'needs_auth'])
                        logger.info(f"Updated session {session.phone} to is_authorized=True based on file presence")
                except Exception as fe:
                    logger.error(f"Error checking session file for {session.phone}: {fe}")
        
        logger.info("Session authorization status updated successfully")
        return True
    except Exception as e:
        logger.error(f"Error updating session auth status: {e}")
        logger.error(traceback.format_exc())
        return False

def main():
    """Main function"""
    logger.info("Starting session authorization fix")
    
    # Add the is_authorized field
    if not add_is_authorized_field():
        logger.error("Failed to add is_authorized field")
        return False
    
    # Update session auth status
    if not update_session_auth_status():
        logger.error("Failed to update session auth status")
        return False
    
    logger.info("Session authorization fix completed successfully")
    return True

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1) 