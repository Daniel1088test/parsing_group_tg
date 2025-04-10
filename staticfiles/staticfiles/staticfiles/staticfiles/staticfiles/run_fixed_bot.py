#!/usr/bin/env python3
"""
Script to run a fully fixed bot with all integration issues resolved
"""
import os
import sys
import logging
import subprocess
import time
import traceback
from pathlib import Path

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('run_fixed_bot.log', encoding='utf-8'),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

# Ensure environment variables are set
os.environ.setdefault('BOT_TOKEN', '8102516142:AAFTsVXXujHHKoX2KZGqZXBHPBznfgh7kg0')
os.environ.setdefault('BOT_USERNAME', 'chan_parsing_mon_bot')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')

def kill_existing_processes():
    """Kill any existing Python processes"""
    try:
        if sys.platform == "win32":
            # Windows
            subprocess.run(["taskkill", "/F", "/IM", "python.exe", "/T"], 
                        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        else:
            # Unix-like
            subprocess.run(["pkill", "-f", "python"], 
                        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        
        # Wait a bit
        time.sleep(2)
        logger.info("Killed existing Python processes")
        return True
    except Exception as e:
        logger.error(f"Error killing processes: {e}")
        return False

def run_fix_scripts():
    """Run all fix scripts"""
    fixes = [
        'fix_bot_integration.py',
        'fix_database_connection.py',
        'fix_all_issues.py'
    ]
    
    for fix in fixes:
        if os.path.exists(fix):
            try:
                logger.info(f"Running {fix}...")
                subprocess.run([sys.executable, fix], check=True)
                logger.info(f"Successfully ran {fix}")
            except subprocess.CalledProcessError:
                logger.warning(f"Fix script {fix} returned non-zero exit code")
            except Exception as e:
                logger.error(f"Error running {fix}: {e}")

def start_bot():
    """Start the bot process"""
    try:
        # First try tg_bot/bot.py directly
        bot_script = 'tg_bot/bot.py'
        if os.path.exists(bot_script):
            logger.info(f"Starting bot using {bot_script}...")
            
            flags = 0
            if sys.platform == "win32":
                flags = subprocess.CREATE_NEW_PROCESS_GROUP | subprocess.DETACHED_PROCESS
                
            process = subprocess.Popen(
                [sys.executable, bot_script],
                creationflags=flags if sys.platform == "win32" else 0,
                start_new_session=True if sys.platform != "win32" else False
            )
            
            logger.info(f"Bot started with PID: {process.pid}")
            return True
        
        # Try alternative scripts
        for script in ['run.py', 'direct_bot_runner.py', 'run_bot.py']:
            if os.path.exists(script):
                logger.info(f"Starting bot using {script}...")
                
                flags = 0
                if sys.platform == "win32":
                    flags = subprocess.CREATE_NEW_PROCESS_GROUP | subprocess.DETACHED_PROCESS
                    
                process = subprocess.Popen(
                    [sys.executable, script],
                    creationflags=flags if sys.platform == "win32" else 0,
                    start_new_session=True if sys.platform != "win32" else False
                )
                
                logger.info(f"Bot started with PID: {process.pid}")
                return True
                
        logger.error("No bot script found to run")
        return False
    except Exception as e:
        logger.error(f"Error starting bot: {e}")
        logger.error(traceback.format_exc())
        return False

def main():
    """Main function"""
    logger.info("=== Starting fixed bot ===")
    
    # Kill existing processes
    kill_existing_processes()
    
    # Run fix scripts
    run_fix_scripts()
    
    # Start the bot
    success = start_bot()
    
    if success:
        logger.info("=== Bot started successfully ===")
        logger.info("The bot is now running in the background.")
        logger.info("You can access it at https://t.me/chan_parsing_mon_bot")
    else:
        logger.error("=== Failed to start bot ===")
        return False
    
    return True

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1) 