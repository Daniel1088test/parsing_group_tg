#!/usr/bin/env python
"""
Create a pre-authorized Telethon session file for deployment to Railway

This script will:
1. Create a fully authorized Telethon session file 
2. Output instructions for uploading to Railway

Usage:
    python create_session_for_railway.py

After running, you'll get a telethon_session.session file that you can upload to Railway.
"""

import os
import sys
import asyncio
import logging
from datetime import datetime
from telethon import TelegramClient, errors

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S',
)
logger = logging.getLogger('create_session')

# API credentials - use the same as in your application
API_ID = 19840544  # Integer value
API_HASH = "c839f28bad345082329ec086fca021fa"  # String value

# Session file to create
SESSION_FILE = "telethon_session"

async def create_authorized_session():
    """Create a fully authorized session file"""
    print("\n=== TELETHON SESSION CREATOR FOR RAILWAY ===")
    print("This script will guide you through creating an authorized session file")
    print("that you can upload to Railway for your production deployment.")
    print("\nThe process:")
    print("1. Enter your phone number")
    print("2. Enter the verification code sent to your Telegram app")
    print("3. Enter your 2FA password (if enabled)")
    print("4. Upload the resulting session file to Railway\n")

    # Check if session file already exists
    if os.path.exists(f"{SESSION_FILE}.session"):
        overwrite = input(f"Session file {SESSION_FILE}.session already exists. Overwrite? (y/n): ").lower()
        if overwrite != 'y':
            print("Aborting. Please move or rename the existing session file.")
            return False
        
    # Create and start the client
    client = TelegramClient(SESSION_FILE, API_ID, API_HASH)
    
    try:
        # Connect and check if already authorized
        await client.connect()
        
        if await client.is_user_authorized():
            me = await client.get_me()
            print(f"\nExisting session is already authorized as: {me.first_name} (@{me.username}) [ID: {me.id}]")
            reauth = input("Do you want to re-authorize anyway? (y/n): ").lower()
            if reauth != 'y':
                print("\nKeeping existing session. Please upload this file to Railway.")
                await client.disconnect()
                return True
        
        # Start authorization process
        print("\nStarting authorization process...")
        print("IMPORTANT: You must use a regular user account, NOT a bot!")
        
        # Get phone number
        phone = input("\nEnter your phone number (with country code, e.g. +380xxxxxxxxx): ")
        
        try:
            # Send code request
            await client.send_code_request(phone)
            print(f"\nVerification code sent to {phone}. Check your Telegram app or SMS.")
            
            # Get verification code
            code = input("Enter the verification code you received: ")
            
            try:
                # Try to sign in with the code
                await client.sign_in(phone, code)
                me = await client.get_me()
                print(f"\n✅ Successfully authorized as: {me.first_name} (@{me.username}) [ID: {me.id}]")
                
            except errors.SessionPasswordNeededError:
                # Two-factor authentication is enabled
                print("\nTwo-factor authentication is enabled.")
                password = input("Enter your 2FA password: ")
                await client.sign_in(password=password)
                me = await client.get_me()
                print(f"\n✅ Successfully authorized with 2FA as: {me.first_name} (@{me.username}) [ID: {me.id}]")
                
            # Create copies for alternative names
            if os.path.exists(f"{SESSION_FILE}.session"):
                for alt_name in ["telethon_user_session", "anon"]:
                    try:
                        import shutil
                        shutil.copy2(f"{SESSION_FILE}.session", f"{alt_name}.session")
                        print(f"Created copy as {alt_name}.session")
                    except Exception as e:
                        print(f"Error creating copy for {alt_name}: {e}")
            
            print("\n=== SESSION CREATED SUCCESSFULLY ===")
            print(f"Session file: {SESSION_FILE}.session")
            
            # Print Railway instructions
            print("\nTo use this session file on Railway:")
            print("1. Upload the .session file to your project")
            print("2. Make sure the file is named 'telethon_session.session'")
            print("3. Restart your application on Railway")
            
            return True
            
        except errors.PhoneCodeInvalidError:
            print("\n❌ Invalid code provided. Please try again.")
            return False
        except errors.PhoneCodeExpiredError:
            print("\n❌ Code expired. Please restart the process.")
            return False
        except errors.FloodWaitError as e:
            hours, remainder = divmod(e.seconds, 3600)
            minutes, seconds = divmod(remainder, 60)
            time_str = ""
            if hours > 0:
                time_str += f"{hours} hours "
            if minutes > 0:
                time_str += f"{minutes} minutes "
            if seconds > 0 or (hours == 0 and minutes == 0):
                time_str += f"{seconds} seconds"
            
            print(f"\n❌ Too many auth attempts! Telegram requires waiting {time_str} before trying again.")
            return False
    
    except Exception as e:
        print(f"\n❌ Error during authorization: {e}")
        import traceback
        print(f"Traceback: {traceback.format_exc()}")
        return False
    
    finally:
        await client.disconnect()

if __name__ == "__main__":
    try:
        asyncio.run(create_authorized_session())
    except KeyboardInterrupt:
        print("\nProcess cancelled by user.")
    except Exception as e:
        print(f"Unexpected error: {e}")
        import traceback
        print(f"Traceback: {traceback.format_exc()}") 