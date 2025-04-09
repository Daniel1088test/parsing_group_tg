#!/usr/bin/env python
"""
Script to start both the Django server and the Telegram bot.
This allows for a single command to start the entire application.
"""

import os
import sys
import subprocess
import time
import signal
import atexit

# Process tracking
processes = []

def cleanup_processes():
    """Kill all child processes on exit"""
    for process in processes:
        try:
            if process.poll() is None:
                process.terminate()
                print(f"Terminated process PID: {process.pid}")
        except:
            pass

# Register the cleanup function to be called on exit
atexit.register(cleanup_processes)

def handle_signal(sig, frame):
    """Handle interrupt signals properly"""
    print("\nReceived shutdown signal. Stopping all processes...")
    cleanup_processes()
    sys.exit(0)

# Set up signal handlers
signal.signal(signal.SIGINT, handle_signal)
signal.signal(signal.SIGTERM, handle_signal)

def start_django():
    """Start the Django development server"""
    print("\n=== Starting Django Server ===")
    
    # Apply database fixes first
    python_path = sys.executable
    
    print("Running database fixes...")
    fix_process = subprocess.run(
        [python_path, "fix_database.py"],
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True
    )
    print(fix_process.stdout)
    
    # Start Django
    django_cmd = [python_path, "manage.py", "runserver", "0.0.0.0:8000"]
    django_process = subprocess.Popen(
        django_cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True
    )
    
    processes.append(django_process)
    print(f"Django server started with PID: {django_process.pid}")
    return django_process

def start_bot():
    """Start the Telegram bot"""
    print("\n=== Starting Telegram Bot ===")
    python_path = sys.executable
    
    # Start the bot
    bot_cmd = [python_path, "run.py"]
    bot_process = subprocess.Popen(
        bot_cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True
    )
    
    processes.append(bot_process)
    print(f"Telegram bot started with PID: {bot_process.pid}")
    return bot_process

def log_output(process, prefix):
    """Log process output with a prefix"""
    while True:
        # Check if process is still running
        if process.poll() is not None:
            print(f"{prefix} process terminated with exit code: {process.returncode}")
            return
        
        # Read and print output
        line = process.stdout.readline()
        if line:
            print(f"{prefix}: {line.strip()}")
        else:
            # If no output, sleep briefly
            time.sleep(0.1)

if __name__ == "__main__":
    print("=== Starting all services ===")
    
    # Start Django
    django_process = start_django()
    
    # Give Django time to start
    time.sleep(5)
    
    # Start the bot
    bot_process = start_bot()
    
    print("\n=== All services started ===")
    print("Press Ctrl+C to stop all services")
    
    # Main loop to monitor processes
    try:
        while True:
            # Check if processes are still running
            for i, process in enumerate(processes):
                if process.poll() is not None:
                    name = "Django" if i == 0 else "Bot"
                    print(f"{name} process terminated with exit code: {process.returncode}")
                    
                    # Restart the process
                    print(f"Restarting {name} process...")
                    if name == "Django":
                        processes[i] = start_django()
                    else:
                        processes[i] = start_bot()
            
            # Sleep before checking again
            time.sleep(1)
    except KeyboardInterrupt:
        print("\nReceived keyboard interrupt. Stopping all processes...")
        cleanup_processes()
    
    print("All services stopped.") 