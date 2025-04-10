#!/usr/bin/env python3
"""
Script to fix integration issues between the bot, admin panel, and session authorization
"""
import os
import sys
import logging
import traceback
import time
import subprocess
from pathlib import Path

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('fix_bot_integration.log', encoding='utf-8'),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

# Ensure environment variables are set
os.environ.setdefault('BOT_TOKEN', '8102516142:AAFTsVXXujHHKoX2KZGqZXBHPBznfgh7kg0')
os.environ.setdefault('BOT_USERNAME', 'chan_parsing_mon_bot')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')

def fix_start_py():
    """
    Fix the start.py handler to properly handle deep link authorization
    """
    try:
        start_py_path = Path('tg_bot/handlers/start.py')
        if not start_py_path.exists():
            logger.error(f"File not found: {start_py_path}")
            return False
        
        with open(start_py_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Check if the start command already properly handles auth tokens
        if 'auth_token =' in content and 'session_id' in content and 'is_authorized = True' in content:
            logger.info("start.py already has auth token handling")
            return True
        
        # Find the cmd_start function
        import re
        cmd_start_match = re.search(r'@router\.message\(CommandStart\(\)\)\nasync def cmd_start\(.*?\):(.*?)(?=@|\Z)', content, re.DOTALL)
        if not cmd_start_match:
            logger.error("Could not find cmd_start function in start.py")
            return False
        
        cmd_start_func = cmd_start_match.group(0)
        
        # Add auth token handling at the beginning of the function
        auth_code = """
    try:
        # Check for deep link parameters (auth token)
        if message.text and len(message.text.split()) > 1:
            auth_token = message.text.split()[1]
            logger.info(f"Received deep link with auth_token: {auth_token}")
            
            # Handle auth token (format: auth_SESSION_ID_TIMESTAMP)
            if auth_token.startswith('auth_'):
                try:
                    parts = auth_token.split('_')
                    if len(parts) >= 3:
                        session_id = int(parts[1])
                        logger.info(f"Processing authorization token for session_id: {session_id}")
                        
                        # Import Django models
                        from django.db import connection
                        from admin_panel.models import TelegramSession
                        
                        # Get the session
                        session = await sync_to_async(TelegramSession.objects.get)(id=session_id)
                        if session:
                            # Mark the session as authorized
                            session.is_authorized = True
                            if hasattr(session, 'needs_auth'):
                                session.needs_auth = False
                            await sync_to_async(session.save)()
                            
                            # Send confirmation to user
                            await message.answer(f"✅ Successfully authorized session for phone: {session.phone}")
                            logger.info(f"Session {session_id} authorized successfully")
                            
                except Exception as auth_error:
                    logger.error(f"Error processing auth token: {auth_error}")
                    await message.answer("❌ Error processing authorization token. Please try again.")
        """
        
        # Find the right place to insert the code
        cmd_start_fixed = re.sub(
            r'(async def cmd_start\(.*?\):\s*)(try:)?',
            r'\1try:\n' + auth_code,
            cmd_start_func
        )
        
        # Replace the original function
        fixed_content = content.replace(cmd_start_func, cmd_start_fixed)
        
        with open(start_py_path, 'w', encoding='utf-8') as f:
            f.write(fixed_content)
        
        logger.info("Fixed start.py to handle auth tokens properly")
        return True
    except Exception as e:
        logger.error(f"Error fixing start.py: {e}")
        logger.error(traceback.format_exc())
        return False

def fix_authorize_session_view():
    """
    Fix the authorize_session_view in admin_panel/views.py
    """
    try:
        views_py_path = Path('admin_panel/views.py')
        if not views_py_path.exists():
            logger.error(f"File not found: {views_py_path}")
            return False
        
        with open(views_py_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Find the authorize_session_view function
        import re
        auth_view_match = re.search(r'def authorize_session_view\(request, session_id\):(.*?)(?=@login_required|\Z)', content, re.DOTALL)
        if not auth_view_match:
            logger.error("Could not find authorize_session_view function in views.py")
            return False
        
        auth_view_func = auth_view_match.group(0)
        
        # Create the fixed function
        fixed_func = """def authorize_session_view(request, session_id):
    \"\"\"View for authorizing a Telegram session directly from the website\"\"\"
    session = get_object_or_404(TelegramSession, pk=session_id)
    
    try:
        # Get bot username from environment or settings
        bot_username = os.environ.get('BOT_USERNAME', 'chan_parsing_mon_bot')
        
        # Generate a unique deep link to the bot
        authorization_token = f"auth_{session_id}_{int(time.time())}"
        deep_link = f"https://t.me/{bot_username}?start={authorization_token}"
        
        # Store the authorization token with the session
        if hasattr(session, 'auth_token'):
            session.auth_token = authorization_token
            session.save(update_fields=['auth_token'])
        
        # Handle form submission for refreshing status
        if request.method == 'POST':
            # Check if the session is now authorized
            session.refresh_from_db()
            if hasattr(session, 'is_authorized') and session.is_authorized:
                messages.success(request, f'Session {session.phone} has been successfully authorized!')
                return redirect('admin_panel:sessions_list')
            else:
                messages.warning(request, f'Session {session.phone} is not yet authorized. Please open the Telegram bot link.')
        
        # Render the template with deep link
        return render(request, 'admin_panel/authorize_session.html', {
            'session': session,
            'deep_link': deep_link,
            'bot_username': bot_username
        })
    except Exception as e:
        logger.error(f"Error in authorize_session_view: {e}")
        logger.error(traceback.format_exc())
        messages.error(request, f"Error authorizing session: {str(e)}")
        return redirect('admin_panel:sessions_list')"""
        
        # Replace the original function
        fixed_content = content.replace(auth_view_func, fixed_func)
        
        with open(views_py_path, 'w', encoding='utf-8') as f:
            f.write(fixed_content)
        
        logger.info("Fixed authorize_session_view in views.py")
        return True
    except Exception as e:
        logger.error(f"Error fixing authorize_session_view: {e}")
        logger.error(traceback.format_exc())
        return False

def fix_telegramsession_model():
    """
    Fix the TelegramSession model to ensure it has the is_authorized field
    """
    try:
        models_py_path = Path('admin_panel/models.py')
        if not models_py_path.exists():
            logger.error(f"File not found: {models_py_path}")
            return False
        
        with open(models_py_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Check if is_authorized field already exists
        if 'is_authorized = models.BooleanField' in content:
            logger.info("TelegramSession model already has is_authorized field")
            return True
        
        # Find the TelegramSession class
        import re
        model_match = re.search(r'class TelegramSession\(models\.Model\):.*?is_bot = models\.BooleanField\(.*?\)', content, re.DOTALL)
        if not model_match:
            logger.error("Could not find TelegramSession.is_bot field in models.py")
            return False
        
        model_part = model_match.group(0)
        
        # Add the is_authorized field
        fixed_model = model_part.replace(
            'is_bot = models.BooleanField(default=False)',
            'is_bot = models.BooleanField(default=False)\n    is_authorized = models.BooleanField(default=False, help_text="Indicates if this session has been authorized via deep link")'
        )
        
        # Replace in the content
        fixed_content = content.replace(model_part, fixed_model)
        
        # Also fix the __str__ method
        str_match = re.search(r'def __str__\(self\):\s*status = "Active" if self\.is_active else "Inactive"\s*auth_status = "[^"]*" if self\.needs_auth else ""', fixed_content)
        if str_match:
            str_part = str_match.group(0)
            fixed_str = str_part + '\n        auth_status = " (Authorized)" if hasattr(self, "is_authorized") and self.is_authorized else auth_status'
            fixed_content = fixed_content.replace(str_part, fixed_str)
        
        with open(models_py_path, 'w', encoding='utf-8') as f:
            f.write(fixed_content)
        
        logger.info("Fixed TelegramSession model to include is_authorized field")
        return True
    except Exception as e:
        logger.error(f"Error fixing TelegramSession model: {e}")
        logger.error(traceback.format_exc())
        return False

def fix_authorize_session_template():
    """
    Fix the authorize_session.html template
    """
    try:
        template_path = Path('templates/admin_panel/authorize_session.html')
        if not template_path.exists():
            logger.warning(f"Template not found: {template_path}")
            # Create template dirs if needed
            template_path.parent.mkdir(parents=True, exist_ok=True)
        
        template_content = """{% extends 'base.html' %}

{% block title %}Authorize Session - {{ session.phone }}{% endblock %}

{% block content %}
<div class="container mt-4">
    <div class="row">
        <div class="col-md-8 offset-md-2">
            <div class="card">
                <div class="card-header bg-primary text-white">
                    <h5 class="card-title mb-0">Authorize Telegram Session</h5>
                </div>
                <div class="card-body text-center">
                    <h4>Authorize Session: {{ session.phone }}</h4>
                    
                    <div class="alert alert-success">
                        <p>Please tap the button below to open the Telegram bot and complete the authorization.</p>
                    </div>
                    
                    <p>Open Telegram Bot to authorize:</p>
                    
                    <div class="my-4">
                        <a href="{{ deep_link }}" class="btn btn-lg btn-primary" target="_blank">
                            <i class="fab fa-telegram"></i> Open Telegram Bot
                        </a>
                    </div>
                    
                    <div class="alert alert-info mt-4">
                        <p>After you authorize via the Telegram bot, return to this page and check the status.</p>
                    </div>
                    
                    <div class="mt-4">
                        <a href="{% url 'admin_panel:sessions_list' %}" class="btn btn-secondary">
                            <i class="fas fa-arrow-left"></i> Back to Sessions List
                        </a>
                        
                        <form method="post" action="" class="d-inline">
                            {% csrf_token %}
                            <button type="submit" class="btn btn-success">
                                <i class="fas fa-sync"></i> Refresh Status
                            </button>
                        </form>
                    </div>
                </div>
            </div>
        </div>
    </div>
</div>
{% endblock %}"""
        
        with open(template_path, 'w', encoding='utf-8') as f:
            f.write(template_content)
        
        logger.info("Fixed authorize_session.html template")
        return True
    except Exception as e:
        logger.error(f"Error fixing authorize_session.html template: {e}")
        logger.error(traceback.format_exc())
        return False

def restart_bot():
    """Restart the bot service"""
    try:
        # Kill existing Python processes
        if sys.platform == "win32":
            # Windows
            subprocess.run(["taskkill", "/F", "/IM", "python.exe", "/T"], 
                        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        else:
            # Unix-like
            subprocess.run(["pkill", "-f", "python"], 
                        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        
        # Wait a bit
        time.sleep(2)
        
        # Start the bot in a new process
        bot_script = None
        for script in ['run.py', 'direct_bot_runner.py', 'run_bot.py']:
            if os.path.exists(script):
                bot_script = script
                break
        
        if not bot_script:
            logger.error("No bot script found to restart")
            return False
        
        flags = 0
        if sys.platform == "win32":
            flags = subprocess.CREATE_NEW_PROCESS_GROUP | subprocess.DETACHED_PROCESS
            
        process = subprocess.Popen(
            [sys.executable, bot_script],
            creationflags=flags if sys.platform == "win32" else 0,
            start_new_session=True if sys.platform != "win32" else False
        )
        
        logger.info(f"Restarted bot using {bot_script}, PID: {process.pid}")
        return True
    except Exception as e:
        logger.error(f"Error restarting bot: {e}")
        logger.error(traceback.format_exc())
        return False

def main():
    """Main function to fix all integration issues"""
    logger.info("Starting bot integration fixes")
    
    # Fix the start.py handler
    fix_start_py()
    
    # Fix the authorize_session_view in views.py
    fix_authorize_session_view()
    
    # Fix the TelegramSession model
    fix_telegramsession_model()
    
    # Fix the authorize_session.html template
    fix_authorize_session_template()
    
    # Restart the bot
    restart_bot()
    
    logger.info("Bot integration fixes completed")
    return True

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1) 