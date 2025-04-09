#!/usr/bin/env python3
"""
Script to fix admin panel queries and ensure safe execution with existing database schema
"""
import os
import sys
import django
import logging
import traceback

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger('fix_admin_query')

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()

# Import needed models
from django.db import connection
from admin_panel.models import Channel, Category, TelegramSession

def fix_channel_session_query():
    """
    Fix potential issues with Channel.session relationship queries
    by checking and fixing the relationship in the database
    """
    try:
        # Check if all Channel.session_id values exist in TelegramSession
        with connection.cursor() as cursor:
            # First check if necessary tables exist
            try:
                cursor.execute("""
                    SELECT 1 
                    FROM information_schema.tables 
                    WHERE table_name = 'admin_panel_channel' 
                    AND table_name = 'admin_panel_telegramsession'
                """)
                if not cursor.fetchone():
                    logger.warning("Required tables don't exist yet. Skipping relationship fix.")
                    return True
            except Exception as e:
                logger.warning(f"Error checking tables: {e}")
                # Continue anyway
            
            # Get channel session IDs that don't have corresponding TelegramSession
            try:
                cursor.execute("""
                    SELECT c.id, c.session_id 
                    FROM admin_panel_channel c
                    LEFT JOIN admin_panel_telegramsession t ON c.session_id = t.id
                    WHERE c.session_id IS NOT NULL AND t.id IS NULL
                """)
                invalid_sessions = cursor.fetchall()
                
                # Set those session_id values to NULL
                if invalid_sessions:
                    logger.info(f"Found {len(invalid_sessions)} channels with invalid session_id values")
                    for channel_id, session_id in invalid_sessions:
                        try:
                            cursor.execute(
                                "UPDATE admin_panel_channel SET session_id = NULL WHERE id = %s",
                                [channel_id]
                            )
                            logger.info(f"Fixed channel {channel_id} (invalid session_id {session_id})")
                        except Exception as update_error:
                            logger.error(f"Error updating channel {channel_id}: {update_error}")
                else:
                    logger.info("No channels with invalid session_id values found")
            except Exception as e:
                logger.error(f"Error checking for invalid session relationships: {e}")
        
        return True
    except Exception as e:
        logger.error(f"Error fixing channel-session relationship: {e}")
        logger.error(traceback.format_exc())
        return False

def add_safe_query_methods():
    """
    Add safe versions of common query methods to models
    """
    try:
        # Add safe_objects manager to Channel model if it doesn't have it already
        if not hasattr(Channel, 'safe_objects'):
            # Define a safe manager for Channel
            from django.db import models
            
            class SafeChannelManager(models.Manager):
                def get_queryset(self):
                    """Return a safe queryset that doesn't use select_related"""
                    return super().get_queryset()
                
                def all_with_safe_session(self):
                    """Try to get channels with session, fallback to all channels if fails"""
                    try:
                        return self.select_related('session').all()
                    except Exception as e:
                        logger.warning(f"select_related('session') failed, falling back: {e}")
                        return self.all()
            
            # Add the safe manager to Channel
            Channel.safe_objects = SafeChannelManager()
            logger.info("Added safe_objects manager to Channel model")
        
        return True
    except Exception as e:
        logger.error(f"Error adding safe query methods: {e}")
        logger.error(traceback.format_exc())
        return False

def main():
    """Main function"""
    logger.info("Starting admin query fixes...")
    
    # Fix channel-session relationship
    fix_channel_session_query()
    
    # Add safe query methods
    add_safe_query_methods()
    
    logger.info("Admin query fixes applied")
    return True

if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        logger.error(f"Unhandled error: {e}")
        logger.error(traceback.format_exc())
        sys.exit(1) 