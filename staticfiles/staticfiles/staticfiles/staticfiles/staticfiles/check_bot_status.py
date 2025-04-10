#!/usr/bin/env python3
"""
Script to check the status of the Telegram bot and verify it's running correctly
"""
import os
import sys
import logging
import subprocess
import requests
import json
import traceback
import time
from pathlib import Path
import psutil

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('bot_status.log', encoding='utf-8'),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

# Bot token from environment
BOT_TOKEN = os.environ.get('BOT_TOKEN', '8102516142:AAFTsVXXujHHKoX2KZGqZXBHPBznfgh7kg0')

def check_bot_api():
    """Check if the bot token is valid and the bot is running via Telegram API"""
    try:
        url = f"https://api.telegram.org/bot{BOT_TOKEN}/getMe"
        response = requests.get(url, timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            if data.get('ok'):
                bot_info = data.get('result', {})
                logger.info(f"Bot API connection successful: @{bot_info.get('username')} (ID: {bot_info.get('id')})")
                return True, bot_info
            else:
                logger.error(f"Bot API error: {data.get('description')}")
                return False, None
        else:
            logger.error(f"Bot API HTTP error: {response.status_code}")
            return False, None
    except Exception as e:
        logger.error(f"Error checking bot API: {e}")
        return False, None

def check_bot_process():
    """Check if the bot process is running"""
    try:
        bot_running = False
        bot_process = None
        python_processes = []
        
        # Get all running Python processes
        for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
            if 'python' in proc.info['name'].lower():
                python_processes.append(proc)
        
        # Look for known bot script patterns
        for proc in python_processes:
            try:
                cmdline = proc.info.get('cmdline', [])
                cmdline_str = ' '.join(cmdline) if cmdline else ''
                
                # Check for known bot scripts
                if any(script in cmdline_str for script in ['tg_bot/bot.py', 'run_bot.py', 'run.py', 'direct_bot_runner.py']):
                    bot_running = True
                    bot_process = proc
                    logger.info(f"Bot process found: PID {proc.pid}, Command: {cmdline_str[:50]}...")
                    break
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue
        
        if not bot_running:
            logger.warning("No bot process found running")
        
        return bot_running, bot_process
    except Exception as e:
        logger.error(f"Error checking bot process: {e}")
        return False, None

def start_bot_if_needed():
    """Start the bot if it's not running"""
    try:
        bot_running, _ = check_bot_process()
        
        if bot_running:
            logger.info("Bot is already running, no need to start")
            return True
        
        logger.info("Bot is not running, attempting to start...")
        
        # Find the right script to run
        bot_scripts = ['tg_bot/bot.py', 'run.py', 'direct_bot_runner.py', 'run_bot.py', 'run_fixed_bot.py']
        script_to_run = None
        
        for script in bot_scripts:
            if os.path.exists(script):
                script_to_run = script
                break
        
        if not script_to_run:
            logger.error("No bot script found to run")
            return False
        
        # Start the bot process
        flags = 0
        if sys.platform == "win32":
            flags = subprocess.CREATE_NEW_PROCESS_GROUP | subprocess.DETACHED_PROCESS
        
        process = subprocess.Popen(
            [sys.executable, script_to_run],
            creationflags=flags if sys.platform == "win32" else 0,
            start_new_session=True if sys.platform != "win32" else False
        )
        
        logger.info(f"Bot started using {script_to_run}, PID: {process.pid}")
        
        # Give it a moment to start up
        time.sleep(5)
        
        # Verify it's running
        bot_running, _ = check_bot_process()
        if bot_running:
            logger.info("Bot started successfully")
            return True
        else:
            logger.error("Failed to start bot process")
            return False
    except Exception as e:
        logger.error(f"Error starting bot: {e}")
        logger.error(traceback.format_exc())
        return False

def main():
    """Main function"""
    logger.info("=== Starting bot status check ===")
    
    # Check if the bot process is running
    bot_proc_running, bot_proc = check_bot_process()
    
    # Check the bot API
    bot_api_running, bot_info = check_bot_api()
    
    # Start the bot if needed
    if not bot_proc_running:
        start_bot_if_needed()
    
    # Display summary
    logger.info("=== Bot Status Summary ===")
    logger.info(f"Bot Process: {'RUNNING' if bot_proc_running else 'NOT RUNNING'}")
    logger.info(f"Bot API: {'WORKING' if bot_api_running else 'NOT WORKING'}")
    
    if bot_info:
        logger.info(f"Bot Username: @{bot_info.get('username', 'unknown')}")
        logger.info(f"Bot Name: {bot_info.get('first_name', 'unknown')}")
    
    if bot_proc_running and bot_api_running:
        logger.info("✅ Bot is fully operational")
        return True
    else:
        logger.warning("⚠️ Bot is not fully operational")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1) 