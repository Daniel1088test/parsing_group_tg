import os
import asyncio
import logging
import argparse
from telethon import TelegramClient, errors
from tg_bot.config import API_ID, API_HASH
import sys
import traceback
from telethon.errors import SessionPasswordNeededError
from admin_panel.models import TelegramSession

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S',
)
logger = logging.getLogger('telethon_auth')

# Налаштування Django для доступу до моделей
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
import django
django.setup()

async def create_session_file(phone, api_id=None, api_hash=None, session_name=None):
    """
    Create a new Telethon session file with authorization
    """
    if not api_id:
        api_id = API_ID
    if not api_hash:
        api_hash = API_HASH
    if not session_name:
        session_name = 'telethon_session'
        
    # Створюємо директорії, якщо вони не існують
    os.makedirs('data/sessions', exist_ok=True)
    
    # Шляхи для файлів сесій
    main_session_path = f"{session_name}.session"
    session_copy_path = f"data/sessions/{session_name}.session"
    
    logger.info(f"Creating new Telethon session for {phone}")
    client = TelegramClient(session_name, api_id, api_hash)
    
    try:
        await client.connect()
        
        if not await client.is_user_authorized():
            logger.info(f"Session not authorized. Starting authorization for {phone}")
            
            # Відправляємо запит на код авторизації
            await client.send_code_request(phone)
            
            # Отримуємо код від користувача
            auth_code = input(f'Enter the code you received for {phone}: ')
            
            try:
                # Авторизуємось з введеним кодом
                await client.sign_in(phone, auth_code)
            except SessionPasswordNeededError:
                # Якщо потрібний пароль двофакторної автентифікації
                password = input("Two-factor authentication is enabled. Please enter your password: ")
                await client.sign_in(password=password)
                
        # Отримуємо інформацію про авторизованого користувача
        me = await client.get_me()
        logger.info(f"Successfully authorized as: {me.first_name} (@{me.username}) [ID: {me.id}]")
        
        # Завантажуємо діалоги для кращої роботи з каналами
        logger.info("Loading dialogs...")
        await client.get_dialogs()
        logger.info("Dialogs loaded")
        
        # Створюємо або оновлюємо запис у базі даних
        try:
            session, created = TelegramSession.objects.get_or_create(
                phone=phone,
                defaults={
                    'api_id': api_id,
                    'api_hash': api_hash,
                    'is_active': True,
                    'session_file': session_name
                }
            )
            
            if not created:
                session.api_id = api_id
                session.api_hash = api_hash
                session.is_active = True
                session.session_file = session_name
                session.save()
                
            logger.info(f"{'Created' if created else 'Updated'} session record in database")
        except Exception as e:
            logger.error(f"Error updating database: {e}")
            logger.error(traceback.format_exc())
        
        # Закриваємо підключення
        await client.disconnect()
        
        # Копіюємо файл сесії в директорію data/sessions
        if os.path.exists(main_session_path) and os.path.isfile(main_session_path):
            import shutil
            try:
                shutil.copy2(main_session_path, session_copy_path)
                logger.info(f"Session file copied to {session_copy_path}")
            except Exception as e:
                logger.error(f"Error copying session file: {e}")
        
        logger.info(f"Session creation completed successfully")
        return True
    except Exception as e:
        logger.error(f"Error creating session: {e}")
        logger.error(traceback.format_exc())
        return False
    finally:
        # Ensure client is disconnected
        try:
            if client and client.is_connected():
                await client.disconnect()
        except:
            pass

async def main():
    """
    Main function to run the script
    """
    print("\n=== Telethon Session Creator ===\n")
    
    # Перевіряємо аргументи командного рядка
    if len(sys.argv) > 1:
        phone = sys.argv[1]
    else:
        phone = input("Enter phone number (with country code, e.g. +380123456789): ")
    
    # Створюємо сесію
    success = await create_session_file(phone)
    
    if success:
        print("\n✅ Session created successfully!")
        print(f"The session file has been created and the session is registered in the database.")
        print(f"You can now use this session for parsing messages from Telegram channels.")
    else:
        print("\n❌ Failed to create session.")
        print("Please check the logs for more information.")

if __name__ == "__main__":
    asyncio.run(main())


