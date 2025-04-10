#!/usr/bin/env python
"""
Telegram Authorization Helper

This script provides an easy way to authorize your Telegram account for use
with the parsing application. It's a simple wrapper around the more complex
tg_bot.auth_telethon module.

Usage:
    python authorize_telegram.py

This will guide you through the steps to authorize your Telegram account.
"""

import os
import sys
import asyncio
import subprocess

def clear_screen():
    """Clear the console screen"""
    os.system('cls' if os.name == 'nt' else 'clear')

def print_title():
    """Print the title banner"""
    clear_screen()
    print("=" * 60)
    print("          TELEGRAM AUTHORIZATION HELPER          ")
    print("=" * 60)
    print()

def main():
    """Main function to run the authorization process"""
    print_title()
    print("This tool will help you authorize your Telegram account")
    print("for use with the parsing application.")
    print()
    print("You'll need:")
    print("  1. Your Telegram phone number (with country code)")
    print("  2. Access to your Telegram account to receive a code")
    print("  3. Your 2FA password (if enabled on your account)")
    print()
    
    choice = input("Do you want to start the authorization process? (y/n): ").lower()
    if choice != 'y':
        print("Authorization cancelled. Exiting...")
        return
    
    print("\nSelect an option:")
    print("1. New authorization (delete any existing session)")
    print("2. Update existing authorization")
    print("3. Force reauthorization (if you're having issues)")
    
    option = input("\nEnter your choice (1-3): ")
    
    cmd = [sys.executable, "-m", "tg_bot.auth_telethon"]
    
    if option == '1':
        cmd.append('--delete')
    elif option == '3':
        cmd.append('--force')
    elif option != '2':
        print("Invalid option. Exiting...")
        return
    
    print("\nStarting authorization process...")
    print("Follow the instructions to authorize your Telegram account.\n")
    
    # Run the authorization process
    try:
        subprocess.run(cmd)
    except KeyboardInterrupt:
        print("\nAuthorization process cancelled.")
        return
    
    print("\nAuthorization process completed.")
    print("If successful, you should now be able to use the parsing application.")
    print("You can restart the application to apply the changes.")

if __name__ == "__main__":
    main() 