import os
import asyncio
import base64
from telethon import TelegramClient
from telethon.sessions import StringSession
from tg_bot.config import API_ID, API_HASH

async def create_session():
    # Create client with StringSession
    client = TelegramClient(StringSession(), API_ID, API_HASH)
    
    try:
        # Connect and sign in
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
        
        # Encode to base64
        encoded_session = base64.b64encode(session_string.encode()).decode()
        
        print("\nSession created successfully!")
        print("\nAdd this to your environment variables:")
        print("Variable name: TELETHON_SESSION")
        print(f"Value: {encoded_session}")
        
    except Exception as e:
        print(f"Error creating session: {e}")
    finally:
        await client.disconnect()

if __name__ == '__main__':
    # Set up Django environment
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
    
    # Run the async function
    asyncio.run(create_session()) 