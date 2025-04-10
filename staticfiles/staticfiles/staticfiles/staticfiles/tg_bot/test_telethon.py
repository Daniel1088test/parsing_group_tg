"""
Script to help test and diagnose Telethon-related issues
"""

import os
import sys
import asyncio
import logging
import traceback
from datetime import datetime

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S',
)
logger = logging.getLogger('telethon_test')

# Try to import config, or use environment variables/defaults
try:
    from tg_bot.config import API_ID, API_HASH
except ImportError:
    logger.warning("Could not import API_ID and API_HASH from config, using hardcoded values")
    # Use hardcoded values to ensure test works
    API_ID = 19840544  # Directly use as integer
    API_HASH = "c839f28bad345082329ec086fca021fa"  # Directly use as string

async def test_ssl():
    """Test SSL library availability"""
    logger.info("Testing SSL library availability...")
    
    try:
        import ssl
        logger.info("✅ SSL module available")
        return True
    except ImportError:
        logger.error("❌ SSL module not available")
        return False

async def test_crypto():
    """Test cryptg module availability for faster encryption"""
    logger.info("Testing cryptg module availability...")
    
    try:
        import cryptg
        logger.info("✅ cryptg module available (faster encryption)")
        return True
    except ImportError:
        logger.warning("⚠️ cryptg module not available. Encryption will be slower.")
        logger.info("To install: pip install cryptg")
        return False

async def test_telethon():
    """Test Telethon import and basic functionality"""
    logger.info("Testing Telethon import...")
    
    try:
        from telethon import TelegramClient, version
        logger.info(f"✅ Telethon imported successfully. Version: {version.__version__}")
        return True
    except ImportError as e:
        logger.error(f"❌ Failed to import Telethon: {e}")
        logger.info("To install: pip install telethon")
        return False
    except Exception as e:
        logger.error(f"❌ Error importing Telethon: {e}")
        return False

async def test_session_files():
    """Check for existing session files"""
    logger.info("Checking for existing session files...")
    
    session_files = ['telethon_user_session.session', 'telethon_session.session', 'anon.session']
    found_files = [file for file in session_files if os.path.exists(file)]
    
    if found_files:
        logger.info(f"✅ Found {len(found_files)} session files: {', '.join(found_files)}")
        return True
    else:
        logger.warning("⚠️ No session files found")
        return False

async def test_client_creation():
    """Test creating a Telethon client"""
    logger.info("Testing Telethon client creation...")
    
    from telethon import TelegramClient
    
    session_name = 'test_session'
    client = None
    
    try:
        # Try normal client creation
        client = TelegramClient(session_name, API_ID, API_HASH)
        logger.info("✅ Created Telethon client successfully")
        
        # Test connection
        logger.info("Testing connection to Telegram servers...")
        await client.connect()
        
        me = None
        try:
            # Check if we're authorized (don't expect to be for a test session)
            if await client.is_user_authorized():
                me = await client.get_me()
                logger.info(f"✅ Successfully connected and authorized as: {me.first_name} (@{me.username})")
            else:
                logger.info("✅ Successfully connected to Telegram (not authorized, which is expected for a test)")
        except Exception as e:
            logger.error(f"❌ Error checking authorization: {e}")
        
        # Test disconnection
        await client.disconnect()
        logger.info("✅ Successfully disconnected from Telegram")
        
        # Clean up test session
        if os.path.exists(f'{session_name}.session'):
            os.remove(f'{session_name}.session')
            logger.info(f"✅ Removed test session file: {session_name}.session")
            
        return True
    except Exception as e:
        logger.error(f"❌ Error creating or using Telethon client: {e}")
        traceback.print_exc()
        
        if client:
            try:
                await client.disconnect()
            except:
                pass
            
        # Clean up test session
        if os.path.exists(f'{session_name}.session'):
            try:
                os.remove(f'{session_name}.session')
                logger.info(f"Removed test session file: {session_name}.session")
            except:
                pass
                
        return False

async def diagnose_telethon():
    """Run a series of diagnostics for Telethon"""
    logger.info("=" * 50)
    logger.info("TELETHON DIAGNOSTIC TOOL")
    logger.info(f"Started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    logger.info(f"Python version: {sys.version}")
    logger.info(f"Operating system: {sys.platform}")
    logger.info("=" * 50)
    
    # Run tests
    ssl_ok = await test_ssl()
    crypto_ok = await test_crypto()
    telethon_ok = await test_telethon()
    
    if not telethon_ok:
        logger.error("Telethon not available. Cannot continue with tests.")
        return False
    
    session_ok = await test_session_files()
    client_ok = await test_client_creation()
    
    # Summary
    logger.info("=" * 50)
    logger.info("DIAGNOSTIC SUMMARY")
    logger.info(f"SSL Module: {'✅ OK' if ssl_ok else '❌ Not available (will use slower fallback)'}")
    logger.info(f"Cryptg Module: {'✅ OK' if crypto_ok else '⚠️ Not available (encryption will be slower)'}")
    logger.info(f"Telethon Import: {'✅ OK' if telethon_ok else '❌ Failed'}")
    logger.info(f"Session Files: {'✅ Found' if session_ok else '⚠️ Not found (will need to create)'}")
    logger.info(f"Client Creation: {'✅ OK' if client_ok else '❌ Failed'}")
    
    # Overall result
    if telethon_ok and client_ok:
        logger.info("✅ OVERALL: Telethon should work properly")
        if not ssl_ok or not crypto_ok:
            logger.info("⚠️ NOTE: Performance may be reduced due to missing SSL or cryptg libraries")
        return True
    else:
        logger.error("❌ OVERALL: Telethon may not work properly")
        logger.info("Please fix the issues above before trying to run the application")
        return False

def create_basic_session():
    """Create a basic session file to help the application start"""
    from tg_bot.create_session import create_session_file
    
    logger.info("Attempting to create a basic session file...")
    
    try:
        asyncio.run(create_session_file())
        logger.info("✅ Created basic session file successfully")
        return True
    except Exception as e:
        logger.error(f"❌ Failed to create basic session file: {e}")
        return False

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description='Test and diagnose Telethon')
    parser.add_argument('--create-session', action='store_true', help='Create a basic session file')
    args = parser.parse_args()
    
    if args.create_session:
        create_basic_session()
    else:
        asyncio.run(diagnose_telethon()) 