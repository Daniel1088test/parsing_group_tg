#!/usr/bin/env python
"""
Fix script to ensure only one bot instance runs at a time.
This prevents the 'terminated by other getUpdates request' conflict error.
"""
import os
import sys
import logging
import subprocess
import psutil
import signal
import time

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler("bot_conflict_fix.log")
    ]
)
logger = logging.getLogger('bot_conflict_fix')

def run_command(command, description="Running command", critical=False):
    """Run a shell command and log the output."""
    logging.info(f"{description}: {command}")
    
    try:
        result = subprocess.run(
            command, 
            shell=True, 
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        logging.info(f"Command output: {result.stdout.strip()}")
        return True
    except subprocess.CalledProcessError as e:
        logging.error(f"Command failed with exit code {e.returncode}")
        logging.error(f"Error output: {e.stderr.strip()}")
        
        if critical:
            logging.critical("Critical command failed. Exiting.")
            sys.exit(1)
        return False

def find_and_kill_telegram_processes():
    """Find and kill any running telegram bot processes"""
    logging.info("Checking for running telegram bot processes")
    
    # Get the current process ID to avoid killing ourselves
    current_pid = os.getpid()
    
    killed_processes = 0
    for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
        try:
            # Skip our own process
            if proc.info['pid'] == current_pid:
                continue
                
            # Check if this is a python process running a bot
            if proc.info['name'] and 'python' in proc.info['name'].lower():
                cmdline = proc.info['cmdline']
                if cmdline and any('bot.py' in cmd for cmd in cmdline if cmd):
                    logging.info(f"Found running bot process: {proc.info['pid']}")
                    
                    # Kill the process
                    try:
                        os.kill(proc.info['pid'], signal.SIGTERM)
                        logging.info(f"Successfully terminated process {proc.info['pid']}")
                        killed_processes += 1
                        # Give process time to shut down
                        time.sleep(2)
                    except Exception as e:
                        logging.error(f"Failed to kill process {proc.info['pid']}: {str(e)}")
        except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
            pass
    
    if killed_processes > 0:
        logging.info(f"Killed {killed_processes} bot processes")
    else:
        logging.info("No running bot processes found")
    
    return killed_processes

def fix_bot_conflict():
    """Fix the telegram bot conflict by ensuring only one instance runs"""
    logging.info("Starting bot conflict fix")
    
    # First, kill any existing bot processes
    killed = find_and_kill_telegram_processes()
    
    logging.info("Bot conflict fix completed")
    return killed > 0

if __name__ == "__main__":
    try:
        fixed = fix_bot_conflict()
        if fixed:
            logging.info("Successfully fixed telegram bot conflict")
        else:
            logging.info("No telegram bot conflicts were found")
        sys.exit(0)
    except Exception as e:
        logging.error(f"Error fixing telegram bot conflict: {str(e)}")
        sys.exit(1) 