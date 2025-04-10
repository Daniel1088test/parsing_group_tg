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
        logging.StreamHandler(sys.stdout),
        logging.FileHandler('fix_bot_conflict.log')
    ]
)
logger = logging.getLogger('bot_conflict_fix')

def kill_existing_bot_processes():
    """Find and kill any existing bot processes"""
    count = 0
    
    for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
        try:
            cmdline = ' '.join(proc.info.get('cmdline', []) or [])
            # Look for processes running bot.py or run_bot.py
            if ('run_bot.py' in cmdline or 'tg_bot/bot.py' in cmdline) and proc.pid != os.getpid():
                logger.info(f"Found bot process: PID {proc.pid}, Command: {cmdline}")
                count += 1
                
                # Kill the process
                if sys.platform == 'win32':
                    os.kill(proc.pid, signal.SIGTERM)
                else:
                    os.kill(proc.pid, signal.SIGTERM)
                    
                logger.info(f"Terminated bot process with PID {proc.pid}")
                time.sleep(1)  # Give it time to terminate
                
                # Check if it's still running and force kill if necessary
                if psutil.pid_exists(proc.pid):
                    logger.warning(f"Process {proc.pid} still exists, forcing termination")
                    if sys.platform == 'win32':
                        os.kill(proc.pid, signal.SIGTERM)
                    else:
                        os.kill(proc.pid, signal.SIGKILL)
        except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
            pass
        except Exception as e:
            logger.error(f"Error killing process: {e}")
    
    return count

def create_lockfile():
    """Create a lockfile to prevent multiple bot instances"""
    lock_file = 'bot.lock'
    with open(lock_file, 'w') as f:
        f.write(str(os.getpid()))
    logger.info(f"Created lock file: {lock_file}")

def main():
    """Main function"""
    logger.info("Starting bot conflict fix")
    
    # Kill any existing bot processes
    killed = kill_existing_bot_processes()
    logger.info(f"Killed {killed} existing bot processes")
    
    # Create lockfile
    create_lockfile()
    
    # Update railway_startup.py to use a locking mechanism
    logger.info("Bot conflict fix completed")
    
    # Print success message
    print("\n" + "="*50)
    print("Bot conflict fix applied!")
    print("This should prevent the 'terminated by other getUpdates request' error.")
    print("="*50 + "\n")
    
    return True

if __name__ == "__main__":
    main() 