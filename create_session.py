import asyncio
from telethon import TelegramClient
from tg_bot.config import API_ID, API_HASH
import os
import django
from asgiref.sync import sync_to_async

# Set up Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()

from admin_panel.models import TelegramSession

@sync_to_async
def get_active_session():
    return TelegramSession.objects.filter(is_active=True).first()

@sync_to_async
def save_session_file(session, file_path):
    session.session_file = file_path
    session.save()

async def create_session():
    # Get the first active session from database
    session = await get_active_session()
    if not session:
        print("No active session found in database")
        return
    
    print(f"Using session with phone: {session.phone}")
    
    # Create the client
    client = TelegramClient('telethon_session', session.api_id, session.api_hash)
    
    try:
        print("Starting client...")
        await client.start()
        
        if await client.is_user_authorized():
            print("Client is already authorized!")
            me = await client.get_me()
            print(f"Logged in as: {me.first_name} (@{me.username})")
        else:
            print("\nClient needs authorization.")
            print(f"Please enter the code you received on {session.phone}")
            await client.send_code_request(session.phone)
            code = input("Enter the code: ")
            await client.sign_in(session.phone, code)
            
            me = await client.get_me()
            print(f"\nSuccessfully logged in as: {me.first_name} (@{me.username})")
        
        # Save the session file path
        await save_session_file(session, 'telethon_session.session')
        
    except Exception as e:
        print(f"Error during authorization: {e}")
    finally:
        await client.disconnect()

if __name__ == '__main__':
    asyncio.run(create_session()) 