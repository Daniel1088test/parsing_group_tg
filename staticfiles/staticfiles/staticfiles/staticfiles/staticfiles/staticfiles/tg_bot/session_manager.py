import os
import base64
import logging
from telethon.sessions import StringSession
from telethon import TelegramClient

logger = logging.getLogger(__name__)

def decode_session_data(session_data: str) -> str:
    """
    Decode base64 session data and return a string session
    """
    try:
        # Add padding if necessary
        padding = 4 - (len(session_data) % 4)
        if padding != 4:
            session_data += '=' * padding
            logger.info(f"Fixed base64 padding (added {padding} padding characters)")
        
        # Decode base64
        decoded_data = base64.b64decode(session_data)
        return decoded_data.decode('utf-8')
    except Exception as e:
        logger.error(f"Failed to decode session data: {e}")
        return None

async def create_client_from_session(api_id: int, api_hash: str, session_data: str) -> TelegramClient:
    """
    Create a Telethon client from session data
    """
    try:
        # Decode session data
        decoded_session = decode_session_data(session_data)
        if not decoded_session:
            return None
            
        # Create string session
        string_session = StringSession(decoded_session)
        
        # Create and start client
        client = TelegramClient(string_session, api_id, api_hash)
        await client.connect()
        
        if not await client.is_user_authorized():
            logger.error("Session is not authorized")
            await client.disconnect()
            return None
            
        return client
    except Exception as e:
        logger.error(f"Failed to create client from session: {e}")
        return None 