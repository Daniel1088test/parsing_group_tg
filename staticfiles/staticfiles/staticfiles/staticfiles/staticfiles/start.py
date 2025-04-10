#!/usr/bin/env python3
"""
Simplified startup script for the Telegram Parser application.
This script runs all the necessary fixes and starts both the Django server and the Telegram bot.
"""
import os
import sys
import subprocess
import logging
import time

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler('start.log')
    ]
)
logger = logging.getLogger('start')

def run_command(command):
    """Run a command and return its success status"""
    try:
        logger.info(f"Running: {command}")
        result = subprocess.run(
            command,
            shell=True,
            check=False,
            capture_output=True,
            text=True
        )
        
        if result.returncode != 0:
            logger.error(f"Command failed: {command}")
            logger.error(f"Error: {result.stderr}")
            return False
        
        logger.info(f"Command succeeded: {command}")
        return True
    except Exception as e:
        logger.error(f"Error running command {command}: {e}")
        return False

def kill_python_processes():
    """Kill any existing Python processes related to the app"""
    if os.name == 'nt':  # Windows
        # More robust process termination for Windows
        try:
            # Kill any processes running run_bot.py
            run_command("tasklist /FI \"IMAGENAME eq python.exe\" /FI \"COMMANDLINE eq *run_bot.py*\" /FO CSV | findstr /V \"CommandLine\" > temp_bot_procs.txt")
            with open("temp_bot_procs.txt", "r") as f:
                for line in f:
                    if "python.exe" in line:
                        try:
                            pid = line.split('","')[1].replace('"', '')
                            run_command(f"taskkill /F /PID {pid}")
                            logger.info(f"Killed bot process with PID {pid}")
                        except:
                            pass
            
            # Clean up temporary file
            if os.path.exists("temp_bot_procs.txt"):
                os.remove("temp_bot_procs.txt")
                
            # Kill Django server processes
            run_command("taskkill /F /IM python.exe /FI \"COMMANDLINE eq *runserver*\" 2>NUL")
        except Exception as e:
            logger.error(f"Error killing processes: {e}")
    else:  # Linux/Unix
        run_command("pkill -f \"python.*run_bot.py\" || true")
        run_command("pkill -f \"python.*runserver\" || true")
        
    # Wait to ensure processes are terminated
    time.sleep(2)
    logger.info("Existing processes terminated")

def setup_environment():
    """Set up the environment and run all fixes"""
    # Run all the fixes sequentially
    fixes = [
        "python fix_templates_and_aiohttp.py",
        "python fix_multiple_fields.py",
        "python fix_admin_query.py"
    ]
    
    for fix in fixes:
        if not run_command(fix):
            logger.warning(f"Fix command had issues: {fix}")
    
    # Collect static files
    run_command("python manage.py collectstatic --noinput")
    
    # Run migrations
    run_command("python manage.py migrate --noinput")
    
    return True

def start_django_server():
    """Start the Django development server"""
    # Start Django in a new process
    if os.name == 'nt':  # Windows
        return subprocess.Popen(
            "start cmd /k python manage.py runserver 0.0.0.0:8000",
            shell=True
        )
    else:  # Linux/Unix
        return subprocess.Popen(
            "python manage.py runserver 0.0.0.0:8000",
            shell=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )

def start_telegram_bot():
    """Start the Telegram bot"""
    # Start bot in a new process
    if os.name == 'nt':  # Windows
        return subprocess.Popen(
            "start cmd /k python run_bot.py",
            shell=True
        )
    else:  # Linux/Unix
        return subprocess.Popen(
            "python run_bot.py",
            shell=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )

def main():
    """Main function"""
    logger.info("Starting application...")
    
    # Kill any existing processes
    kill_python_processes()
    
    # Set up environment and run fixes
    if not setup_environment():
        logger.error("Failed to set up environment")
        return False
    
    # Start Django server
    django_process = start_django_server()
    logger.info("Django server started")
    
    # Give Django time to start
    time.sleep(5)
    
    # Start Telegram bot
    bot_process = start_telegram_bot()
    logger.info("Telegram bot started")
    
    logger.info("Application startup complete.")
    
    # Print success message to console
    print("\n" + "="*50)
    print("Application started successfully!")
    print("- Django server running at http://localhost:8000")
    print("- Telegram bot running")
    print("\nPress Ctrl+C in each terminal window to stop the services")
    print("="*50 + "\n")
    
    return True

if __name__ == "__main__":
    main() 