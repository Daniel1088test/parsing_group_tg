import os
import django
import logging

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()

from admin_panel.models import TelegramSession

def test_get_session():
    try:
        # Try to get all sessions
        sessions = TelegramSession.objects.all()
        logger.info(f"Found {len(sessions)} sessions")
        
        for session in sessions:
            logger.info(f"Session ID: {session.id}, Phone: {session.phone}, Active: {session.is_active}")
            
        # Try to get session with ID 2
        session_id = 2
        try:
            session = TelegramSession.objects.filter(id=session_id).values(
                'id', 'phone', 'api_id', 'api_hash', 'is_active', 'session_file'
            ).first()
            
            if session:
                logger.info(f"Successfully retrieved session ID {session_id}: {session['phone']}")
            else:
                logger.warning(f"Session ID {session_id} not found")
        except Exception as e:
            logger.error(f"Error retrieving session ID {session_id}: {str(e)}")
            
    except Exception as e:
        logger.error(f"Error: {str(e)}")

if __name__ == "__main__":
    test_get_session() 