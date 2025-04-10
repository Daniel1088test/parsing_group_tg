#!/usr/bin/env python3
"""
Script to run all components: Django web server, Telegram bot, and database fixes
"""
import os
import sys
import logging
import subprocess
import time
import threading
import signal
import django

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler('run_all.log')
    ]
)
logger = logging.getLogger('run_all')

# Initialize Django settings
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')

try:
    django.setup()
    from django.conf import settings
    logger.info("Django initialized successfully")
except Exception as e:
    logger.error(f"Error initializing Django: {e}")
    sys.exit(1)

# Define processes to run
processes = {
    'django': None,
    'bot': None,
}

def run_command(command, env=None):
    """Run a shell command and capture output"""
    try:
        env_vars = os.environ.copy()
        if env:
            env_vars.update(env)
        
        result = subprocess.run(
            command,
            shell=True,
            capture_output=True,
            text=True,
            check=False,
            env=env_vars
        )
        
        if result.returncode != 0:
            logger.error(f"Command failed: {command}")
            logger.error(f"Output: {result.stdout}")
            logger.error(f"Error: {result.stderr}")
            return False
        
        logger.info(f"Command succeeded: {command}")
        return True
    except Exception as e:
        logger.error(f"Error running command {command}: {e}")
        return False

def run_database_fixes():
    """Run database fix scripts"""
    logger.info("Running database fixes...")
    
    # Fix templates and static files
    run_command("python fix_templates_and_aiohttp.py")
    
    # Fix database fields
    run_command("python fix_multiple_fields.py")
    
    # Fix admin queries
    run_command("python fix_admin_query.py")
    
    logger.info("Database fixes completed")

def run_django_server():
    """Run Django development server"""
    try:
        logger.info("Starting Django server...")
        cmd = "python manage.py runserver 0.0.0.0:8000"
        
        # Use different command in production (Railway)
        if os.environ.get('RAILWAY_ENVIRONMENT') or os.environ.get('PORT'):
            port = os.environ.get('PORT', '8000')
            cmd = f"python manage.py runserver 0.0.0.0:{port}"
        
        processes['django'] = subprocess.Popen(
            cmd,
            shell=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1,
            universal_newlines=True
        )
        
        logger.info(f"Django server started with PID {processes['django'].pid}")
        
        # Monitor output in a separate thread
        def monitor_output():
            for line in iter(processes['django'].stdout.readline, ''):
                print(f"[Django] {line.strip()}")
            processes['django'].stdout.close()
            
        threading.Thread(target=monitor_output, daemon=True).start()
        
    except Exception as e:
        logger.error(f"Error starting Django server: {e}")

def run_telegram_bot():
    """Run Telegram bot"""
    try:
        logger.info("Starting Telegram bot...")
        
        processes['bot'] = subprocess.Popen(
            "python run_bot.py",
            shell=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1,
            universal_newlines=True
        )
        
        logger.info(f"Telegram bot started with PID {processes['bot'].pid}")
        
        # Monitor output in a separate thread
        def monitor_output():
            for line in iter(processes['bot'].stdout.readline, ''):
                print(f"[Bot] {line.strip()}")
            processes['bot'].stdout.close()
            
        threading.Thread(target=monitor_output, daemon=True).start()
        
    except Exception as e:
        logger.error(f"Error starting Telegram bot: {e}")

def signal_handler(sig, frame):
    """Handle termination signals"""
    logger.info("Termination signal received, shutting down...")
    
    # Terminate all processes
    for name, process in processes.items():
        if process is not None and process.poll() is None:
            logger.info(f"Terminating {name} process (PID: {process.pid})...")
            try:
                process.terminate()
                process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                logger.warning(f"Process {name} did not terminate gracefully, killing...")
                process.kill()
            except Exception as e:
                logger.error(f"Error terminating {name} process: {e}")
    
    logger.info("All processes terminated")
    sys.exit(0)

def main():
    """Main function"""
    logger.info("Starting all components...")
    
    # Register signal handlers
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    # Run database fixes
    run_database_fixes()
    
    # Run Django server
    run_django_server()
    
    # Run Telegram bot
    run_telegram_bot()
    
    logger.info("All components started")
    
    # Keep main thread alive
    try:
        while True:
            # Check if processes are still running
            for name, process in processes.items():
                if process is not None and process.poll() is not None:
                    logger.error(f"{name} process terminated unexpectedly with return code {process.returncode}")
                    
                    # Restart the process
                    logger.info(f"Restarting {name} process...")
                    if name == 'django':
                        run_django_server()
                    elif name == 'bot':
                        run_telegram_bot()
            
            time.sleep(5)
    except KeyboardInterrupt:
        logger.info("Keyboard interrupt received")
        signal_handler(signal.SIGINT, None)
    
    logger.info("Exiting main process")

if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        logger.error(f"Unhandled error: {e}")
        sys.exit(1) 