import os
import django
import asyncio
import base64
from telethon import TelegramClient
from telethon.sessions import StringSession

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()

from admin_panel.models import TelegramSession
from tg_bot.config import API_ID, API_HASH

async def create_session():
    # Create client with StringSession
    client = TelegramClient(StringSession(), API_ID, API_HASH)
    
    try:
        print("Starting session creation...")
        await client.connect()
        
        if not await client.is_user_authorized():
            # Ask for phone number
            phone = input('Enter your phone number (with country code): ')
            
            # Send code request
            await client.send_code_request(phone)
            
            # Ask for the code
            code = input('Enter the code you received: ')
            
            # Sign in
            await client.sign_in(phone, code)
            
            # If 2FA is enabled, ask for password
            if await client.is_user_authorized():
                print("Successfully signed in!")
            else:
                password = input('Enter your 2FA password: ')
                await client.sign_in(password=password)
        
        # Get the session string
        session_string = client.session.save()
        
        # Create or update session in database
        session = TelegramSession.objects.create(
            phone=phone,
            api_id=API_ID,
            api_hash=API_HASH,
            session_data=session_string,
            is_active=True
        )
        
        print("\nSession created successfully!")
        print(f"Session ID: {session.id}")
        print(f"Phone: {session.phone}")
        
    except Exception as e:
        print(f"Error creating session: {e}")
    finally:
        await client.disconnect()

if __name__ == '__main__':
    asyncio.run(create_session()) 