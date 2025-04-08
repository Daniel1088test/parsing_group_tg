#!/usr/bin/env python
"""
Launcher script for the Telegram Bot and Parser.
Handles starting, monitoring, and graceful shutdown of both processes.
"""
import os
import sys
import logging
import subprocess
import time
import signal
from pathlib import Path

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S',
)
logger = logging.getLogger('tg_launcher')

# Add the project root to the Python path
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(current_dir)
sys.path.insert(0, project_root)

# Set environment variable for Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')

# Paths to the bot and parser scripts
BOT_SCRIPT = os.path.join(current_dir, 'bot.py')
PARSER_SCRIPT = os.path.join(project_root, 'run_parser.py')

class ProcessManager:
    """Manages child processes for the bot and parser."""
    
    def __init__(self):
        self.processes = {}
        self.running = True
        
    def start_process(self, name, script_path):
        """Start a Python process."""
        try:
            logger.info(f"Starting {name} process...")
            
            # Ensure the script exists
            if not os.path.exists(script_path):
                logger.error(f"Script not found: {script_path}")
                return None
                
            # Create log file directory if it doesn't exist
            log_dir = os.path.join(project_root, 'logs')
            os.makedirs(log_dir, exist_ok=True)
            
            # Open log files
            stdout_path = os.path.join(log_dir, f"{name}_stdout.log")
            stderr_path = os.path.join(log_dir, f"{name}_stderr.log")
            
            stdout_file = open(stdout_path, 'a')
            stderr_file = open(stderr_path, 'a')
            
            # Start the process
            process = subprocess.Popen(
                [sys.executable, script_path],
                stdout=stdout_file,
                stderr=stderr_file,
                cwd=project_root,  # Set working directory to project root
                env=os.environ.copy()  # Pass current environment variables
            )
            
            self.processes[name] = {
                'process': process,
                'stdout': stdout_file,
                'stderr': stderr_file
            }
            
            logger.info(f"{name} process started (PID: {process.pid})")
            return process
        except Exception as e:
            logger.error(f"Failed to start {name}: {e}")
            import traceback
            logger.error(traceback.format_exc())
            return None
            
    def monitor_processes(self):
        """Monitor and restart processes if they crash."""
        while self.running:
            for name, proc_info in list(self.processes.items()):
                process = proc_info['process']
                # Check if process is still running
                return_code = process.poll()
                if return_code is not None:
                    logger.warning(f"{name} process exited with code {return_code}")
                    
                    # Restart the process if it's supposed to be running
                    if self.running:
                        logger.info(f"Restarting {name} process...")
                        script_path = BOT_SCRIPT if name == "bot" else PARSER_SCRIPT
                        # Close old file handles
                        proc_info['stdout'].close()
                        proc_info['stderr'].close()
                        # Start the process again
                        self.start_process(name, script_path)
            
            # Short sleep to prevent CPU overuse
            time.sleep(2)
    
    def stop_all(self):
        """Stop all running processes."""
        logger.info("Stopping all processes...")
        self.running = False
        
        for name, proc_info in self.processes.items():
            process = proc_info['process']
            try:
                logger.info(f"Stopping {name} process (PID: {process.pid})...")
                process.terminate()
                # Give it a moment to terminate gracefully
                process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                logger.warning(f"{name} process didn't terminate gracefully, killing...")
                process.kill()
            except Exception as e:
                logger.error(f"Error stopping {name} process: {e}")
            finally:
                # Close file handles
                proc_info['stdout'].close()
                proc_info['stderr'].close()
        
        logger.info("All processes stopped")

def signal_handler(sig, frame):
    """Handle termination signals."""
    logger.info(f"Received signal {sig}, shutting down...")
    if process_manager:
        process_manager.stop_all()
    sys.exit(0)

# Global process manager
process_manager = None

if __name__ == "__main__":
    # Set up signal handlers
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    logger.info("Starting Telegram Bot and Parser services...")
    
    try:
        # Create process manager
        process_manager = ProcessManager()
        
        # Start the bot and parser
        bot_process = process_manager.start_process("bot", BOT_SCRIPT)
        parser_process = process_manager.start_process("parser", PARSER_SCRIPT)
        
        if not bot_process or not parser_process:
            logger.warning("Failed to start one or more processes")
        
        # Monitor the processes
        process_manager.monitor_processes()
        
    except KeyboardInterrupt:
        logger.info("Interrupted by user")
    except Exception as e:
        logger.error(f"Error in main process: {e}")
        import traceback
        logger.error(traceback.format_exc())
    finally:
        # Ensure all processes are stopped
        if process_manager:
            process_manager.stop_all()
        
        logger.info("Exiting") 