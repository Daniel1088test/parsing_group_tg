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
                """)
                if not cursor.fetchone():
                    logger.warning("Channel table doesn't exist yet. Skipping relationship fix.")
                    return True
                
                cursor.execute("""
                    SELECT 1 
                    FROM information_schema.tables 
                    WHERE table_name = 'admin_panel_telegramsession'
                """)
                if not cursor.fetchone():
                    logger.warning("TelegramSession table doesn't exist yet. Skipping relationship fix.")
                    return True
            except Exception as e:
                logger.warning(f"Error checking tables: {e}")
                # Continue anyway since this might be a SQLite database that doesn't support this query
            
            # Try a simpler approach that works in both PostgreSQL and SQLite
            try:
                # Check if the session_id column exists in the channel table
                try:
                    cursor.execute("SELECT session_id FROM admin_panel_channel LIMIT 1")
                except Exception as column_error:
                    logger.warning(f"session_id column doesn't exist in Channel model: {column_error}")
                    return True
                
                # Get all channel session_id values
                cursor.execute("SELECT id, session_id FROM admin_panel_channel WHERE session_id IS NOT NULL")
                channels_with_sessions = cursor.fetchall()
                
                if not channels_with_sessions:
                    logger.info("No channels with assigned sessions found")
                    return True
                
                # Get all session IDs
                cursor.execute("SELECT id FROM admin_panel_telegramsession")
                valid_session_ids = [row[0] for row in cursor.fetchall()]
                
                # Find channels with invalid session IDs
                invalid_channels = []
                for channel_id, session_id in channels_with_sessions:
                    if session_id not in valid_session_ids:
                        invalid_channels.append((channel_id, session_id))
                
                # Fix invalid references
                if invalid_channels:
                    logger.info(f"Found {len(invalid_channels)} channels with invalid session_id values")
                    for channel_id, session_id in invalid_channels:
                        cursor.execute(
                            "UPDATE admin_panel_channel SET session_id = NULL WHERE id = ?",
                            [channel_id]
                        )
                        logger.info(f"Fixed channel {channel_id} (invalid session_id {session_id})")
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