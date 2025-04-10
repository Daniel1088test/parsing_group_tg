#!/usr/bin/env python3
"""
Simple direct script to start the Telegram bot
"""
import os
import sys
import subprocess

# Set environment variables
os.environ['BOT_TOKEN'] = "8102516142:AAFTsVXXujHHKoX2KZGqZXBHPBznfgh7kg0"
os.environ['BOT_USERNAME'] = "chan_parsing_mon_bot"

# Try to start the bot directly
print("Starting Telegram bot...")
bot_path = os.path.join('tg_bot', 'bot.py')

if os.path.exists(bot_path):
    # Start bot in foreground to see any errors
    print(f"Running: python {bot_path}")
    try:
        subprocess.run([sys.executable, bot_path], check=True)
    except KeyboardInterrupt:
        print("\nBot stopped by user")
    except Exception as e:
        print(f"Error starting bot: {e}")
else:
    print(f"Bot file not found: {bot_path}")
    
    # Try alternate bot scripts
    alt_scripts = ['run.py', 'direct_bot_runner.py', 'run_bot.py']
    for script in alt_scripts:
        if os.path.exists(script):
            print(f"Found alternate script: {script}")
            print(f"Running: python {script}")
            try:
                subprocess.run([sys.executable, script], check=True)
                break
            except KeyboardInterrupt:
                print("\nBot stopped by user")
                break
            except Exception as e:
                print(f"Error running {script}: {e}")
    else:
        print("No bot scripts found. Please check your installation.")
