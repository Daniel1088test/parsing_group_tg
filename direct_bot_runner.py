#!/usr/bin/env python3
"""
Simplified direct bot runner for Railway deployment.
Handles aiohttp session closing and other common issues.
"""
import os
import sys
import logging
import asyncio
import signal
import traceback
import gc

# Set up environment variables directly from Railway
os.environ['BOT_TOKEN'] = "8102516142:AAFTsVXXujHHKoX2KZGqZXBHPBznfgh7kg0"
os.environ['API_ID'] = "19840544"
os.environ['API_HASH'] = "c839f28bad345082329ec086fca021fa"
os.environ['PGHOST'] = "postgres.railway.internal"
os.environ['PGPORT'] = "5432"
os.environ['PGUSER'] = "postgres"
os.environ['PGPASSWORD'] = "urCNhXdwvbqOvvEsJDffIiDUMcLhAvcs"
os.environ['PGDATABASE'] = "railway"
os.environ['DATABASE_URL'] = "postgresql://postgres:urCNhXdwvbqOvvEsJDffIiDUMcLhAvcs@postgres.railway.internal:5432/railway"

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('logs/direct_bot.log', encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger('direct_bot_runner')

# Set up Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
try:
    import django
    django.setup()
    logger.info("Django setup successful")
except Exception as e:
    logger.error(f"Django setup error: {e}")

# Keep track of created sessions
created_sessions = []

# Signal handlers for graceful shutdown
def signal_handler(sig, frame):
    logger.info(f"Received signal {sig}, shutting down...")
    sys.exit(0)

signal.signal(signal.SIGINT, signal_handler)
signal.signal(signal.SIGTERM, signal_handler)

async def close_sessions():
    """Close any open aiohttp sessions to prevent warnings"""
    import aiohttp
    
    # Find any aiohttp sessions in global objects
    for obj in gc.get_objects():
        if isinstance(obj, aiohttp.ClientSession) and not obj.closed:
            logger.info("Closing unclosed aiohttp session")
            try:
                await obj.close()
            except Exception as e:
                logger.error(f"Error closing session: {e}")
    
    # Also close any sessions we tracked
    for session in created_sessions:
        if not session.closed:
            try:
                logger.info("Closing tracked session")
                await session.close()
            except Exception as e:
                logger.error(f"Error closing tracked session: {e}")

async def verify_bot_token():
    """Verify the bot token is valid by connecting to Telegram API"""
    try:
        from aiogram import Bot
        
        # Use the token directly from environment
        token = "8102516142:AAFTsVXXujHHKoX2KZGqZXBHPBznfgh7kg0"
        
        # Try to connect to Telegram API
        bot = Bot(token=token)
        me = await bot.get_me()
        logger.info(f"✓ Bot connection verified: @{me.username} (ID: {me.id})")
        
        # Close the session properly
        try:
            session = bot.session
            if hasattr(session, 'close') and callable(session.close):
                await session.close()
                logger.info("Bot session closed properly")
        except Exception as e:
            logger.error(f"Error closing bot session: {e}")
        
        return True
    except Exception as e:
        logger.error(f"Bot token verification failed: {e}")
        logger.error(traceback.format_exc())
        return False

async def setup_bot_commands(bot):
    """Set up default bot commands"""
    try:
        from aiogram.types import BotCommand, BotCommandScopeDefault
        
        commands = [
            BotCommand(command='start', description='Start the bot and show main menu'),
            BotCommand(command='menu', description='Show the main menu'),
            BotCommand(command='help', description='Show help'),
            BotCommand(command='authorize', description='Start authorization process')
        ]
        
        await bot.set_my_commands(commands=commands, scope=BotCommandScopeDefault())
        logger.info("Bot commands registered successfully")
    except Exception as e:
        logger.error(f"Error setting bot commands: {e}")

async def run_bot():
    """Run the bot with proper error handling and session cleanup"""
    try:
        # First verify the bot token
        if not await verify_bot_token():
            logger.error("Cannot start bot with invalid token")
            return
        
        try:
            # Try with direct import first
            from tg_bot.bot import main, bot, dp
            logger.info("Successfully imported bot directly")
        except ImportError:
            # If that fails, try importing the module
            try:
                import tg_bot.bot
                main = tg_bot.bot.main
                bot = tg_bot.bot.bot
                dp = tg_bot.bot.dp
                logger.info("Successfully imported bot via module")
            except (ImportError, AttributeError) as e:
                logger.error(f"Failed to import the bot: {e}")
                return
        
        # Set up bot commands
        await setup_bot_commands(bot)
        
        # Get bot session for cleanup
        if hasattr(bot, 'session'):
            created_sessions.append(bot.session)
        
        # Run the main bot function
        logger.info("Starting bot main function...")
        await main()
    except Exception as e:
        logger.error(f"Error running bot: {e}")
        logger.error(traceback.format_exc())
    finally:
        # Always close sessions at the end
        await close_sessions()

if __name__ == "__main__":
    try:
        # Run with proper cleanup even on exceptions
        asyncio.run(run_bot())
    except KeyboardInterrupt:
        logger.info("Bot stopped by keyboard interrupt")
    except Exception as e:
        logger.error(f"Fatal error in direct_bot_runner: {e}")
        logger.error(traceback.format_exc())
    finally:
        # Try one more time to close sessions synchronously
        import gc
        import aiohttp
        
        for obj in gc.get_objects():
            if isinstance(obj, aiohttp.ClientSession):
                logger.info("Found unclosed session after bot run")
                obj._connector._close()
                logger.info("Forced connector close")
        
        logger.info("Bot runner completed") 