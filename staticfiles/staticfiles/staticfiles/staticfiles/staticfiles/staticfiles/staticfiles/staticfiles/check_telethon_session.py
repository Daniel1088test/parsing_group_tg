#!/usr/bin/env python
import os
import base64
import logging
import sys

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S',
)
logger = logging.getLogger('check_telethon_session')

def check_telethon_session():
    """
    Check the TELETHON_SESSION environment variable
    """
    session_data = os.getenv('TELETHON_SESSION')
    if not session_data:
        logger.error("TELETHON_SESSION environment variable is not set")
        return False
        
    if not session_data.strip():
        logger.error("TELETHON_SESSION environment variable is empty or whitespace only")
        return False
        
    logger.info(f"TELETHON_SESSION length: {len(session_data)}")
    
    # Check if it's valid base64
    try:
        # Fix padding
        if len(session_data) % 4 != 0:
            padding = 4 - (len(session_data) % 4)
            session_data += "=" * padding
            logger.info(f"Fixed base64 padding (added {padding} padding characters)")
        
        # Try to decode
        decoded_data = base64.b64decode(session_data)
        logger.info(f"Successfully decoded base64 session data ({len(decoded_data)} bytes)")
        
        # Write to temporary file for inspection
        with open('telethon_session_test.session', 'wb') as f:
            f.write(decoded_data)
            
        logger.info(f"Wrote decoded data to telethon_session_test.session")
        
        # Try to check if it's a valid SQLite database
        try:
            import sqlite3
            conn = sqlite3.connect('telethon_session_test.session')
            cursor = conn.cursor()
            
            # Check tables
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
            tables = [row[0] for row in cursor.fetchall()]
            logger.info(f"Tables in session file: {tables}")
            
            # Check if important Telethon tables exist
            required_tables = ['sessions', 'entities']
            for table in required_tables:
                if table not in tables:
                    logger.error(f"Required table '{table}' not found in session file")
                else:
                    logger.info(f"Required table '{table}' exists")
                    
            # Check sessions table content
            cursor.execute("SELECT COUNT(*) FROM sessions;")
            session_count = cursor.fetchone()[0]
            logger.info(f"Number of sessions in file: {session_count}")
            
            # Close database
            conn.close()
            
        except sqlite3.Error as e:
            logger.error(f"SQLite error: {e}")
            return False
        except Exception as e:
            logger.error(f"Error checking SQLite structure: {e}")
            return False
            
        return True
    except Exception as e:
        logger.error(f"Error decoding base64: {e}")
        return False

if __name__ == "__main__":
    print("Checking TELETHON_SESSION environment variable...")
    success = check_telethon_session()
    if success:
        print("TELETHON_SESSION appears to be valid")
        sys.exit(0)
    else:
        print("TELETHON_SESSION appears to be invalid")
        sys.exit(1) 