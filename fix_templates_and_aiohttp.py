#!/usr/bin/env python3
"""
Script to fix template issues and aiohttp session closure
"""
import os
import sys
import logging
import importlib
import django
from django.core.management import call_command
import asyncio
import subprocess
from pathlib import Path
import shutil

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('fix_templates.log')
    ]
)
logger = logging.getLogger('fix_templates')

def ensure_directory(directory_path):
    """Ensure directory exists"""
    try:
        os.makedirs(directory_path, exist_ok=True)
        logger.info(f"Ensured directory exists: {directory_path}")
        return True
    except Exception as e:
        logger.error(f"Error creating directory {directory_path}: {e}")
        return False

def apply_migrations():
    """Apply database migrations"""
    try:
        os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
        django.setup()
        
        logger.info("Running makemigrations")
        call_command('makemigrations')
        
        logger.info("Running migrate")
        call_command('migrate')
        
        logger.info("Migrations completed successfully")
        return True
    except Exception as e:
        logger.error(f"Error applying migrations: {e}")
        return False

def check_templates():
    """Check and fix template paths"""
    try:
        # Ensure template directories exist
        templates_dir = Path('templates')
        admin_panel_templates = templates_dir / 'admin_panel'
        admin_panel_app_templates = Path('admin_panel/templates/admin_panel')
        
        ensure_directory(templates_dir)
        ensure_directory(admin_panel_templates)
        
        # Check if admin_panel templates are available
        if admin_panel_app_templates.exists():
            # Copy templates from app directory to main templates directory if needed
            for template_file in admin_panel_app_templates.glob('*.html'):
                target_file = admin_panel_templates / template_file.name
                if not target_file.exists():
                    shutil.copy2(template_file, target_file)
                    logger.info(f"Copied template {template_file.name} to main templates directory")
        
        # Create base.html if it doesn't exist
        base_template = templates_dir / 'base.html'
        if not base_template.exists():
            # Copy from the app if it exists there
            app_base = Path('admin_panel/templates/base.html')
            if app_base.exists():
                shutil.copy2(app_base, base_template)
                logger.info(f"Copied base.html from app templates")
            else:
                # Create a minimal base template
                with open(base_template, 'w') as f:
                    f.write("""<!DOCTYPE html>
<html lang="uk">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{% block title %}Telegram Parser{% endblock %}</title>
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.2/dist/css/bootstrap.min.css" rel="stylesheet">
    {% block extra_css %}{% endblock %}
</head>
<body>
    {% block content %}{% endblock %}
    <script src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.2/dist/js/bootstrap.bundle.min.js"></script>
    {% block extra_js %}{% endblock %}
</body>
</html>""")
                logger.info("Created minimal base.html template")
        
        logger.info("Template check completed")
        return True
    except Exception as e:
        logger.error(f"Error checking templates: {e}")
        return False

def fix_aiohttp_sessions():
    """Add proper cleanup for aiohttp sessions in the bot code"""
    try:
        # Check for bot.py file
        bot_file = Path('tg_bot/bot.py')
        if not bot_file.exists():
            logger.warning(f"Bot file not found at {bot_file}")
            return False
        
        # Read bot.py
        with open(bot_file, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Check if session closure is already implemented
        if 'await close_all_sessions()' in content:
            logger.info("Session closure already implemented in bot.py")
            return True
        
        # Add session closure function if not present
        session_cleanup_code = """
# Function to close all aiohttp sessions
async def close_all_sessions():
    # Close all aiohttp sessions to prevent unclosed session warnings
    import gc
    import aiohttp
    
    for obj in gc.get_objects():
        if isinstance(obj, aiohttp.ClientSession) and not obj.closed:
            logger.info(f"Closing unclosed ClientSession: {obj!r}")
            await obj.close()
    logger.info("All aiohttp sessions closed")
"""
        
        # Add cleanup to shutdown handlers
        main_function_update = """
async def main():
    # Main function to run the bot
    try:
        bot_commands = [
            BotCommand(command="start", description="Start the bot"),
            BotCommand(command="menu", description="Show the main menu"),
            BotCommand(command="help", description="Show help information"),
        ]
        await bot.set_my_commands(bot_commands)
        
        # Register shutdown handler
        async def shutdown():
            # Shutdown handler to close resources properly
            logger.info("Shutting down...")
            # Close the session
            try:
                await close_all_sessions()
            except Exception as e:
                logger.error(f"Error closing sessions: {e}")
            
            # Stop the dispatcher
            await dp.stop_polling()
            logger.info("Bot stopped")
        
        # Add shutdown to signal handlers
        dp.shutdown.register(shutdown)
        
        # Start the bot
        await dp.start_polling(bot, skip_updates=False)
    except Exception as e:
        logger.error(f"Error running bot: {e}")
        raise
"""
        
        # Check if we need to replace main function
        if "async def main():" in content and "await dp.start_polling" in content:
            # Replace the main function
            import re
            pattern = r"async def main\(\):.*?(?=if __name__ == ['\"]__main__['\"]:|$)"
            new_content = re.sub(pattern, main_function_update, content, flags=re.DOTALL)
            
            # Add session cleanup function before main
            if "async def close_all_sessions():" not in new_content:
                # Find a good spot to insert it - before main function
                main_index = new_content.find("async def main()")
                if main_index > 0:
                    # Find the last import or global variable before main
                    lines = new_content[:main_index].splitlines()
                    insert_index = 0
                    for i, line in enumerate(lines):
                        if line.strip() and not line.strip().startswith('#'):
                            insert_index = new_content.find(line) + len(line)
                    
                    if insert_index > 0:
                        new_content = new_content[:insert_index] + session_cleanup_code + new_content[insert_index:]
                    else:
                        # Just insert at the beginning of the main function
                        new_content = new_content[:main_index] + session_cleanup_code + new_content[main_index:]
            
            # Save updated file
            with open(bot_file, 'w', encoding='utf-8') as f:
                f.write(new_content)
            
            logger.info("Updated bot.py with proper session cleanup")
            return True
        else:
            logger.warning("Could not locate main function in bot.py, manual fix required")
            return False
    except Exception as e:
        logger.error(f"Error fixing aiohttp sessions: {e}")
        return False

def create_placeholder_templates():
    """Create placeholder templates for common pages"""
    try:
        templates_dir = Path('templates')
        admin_panel_templates = templates_dir / 'admin_panel'
        
        # Ensure directories exist
        ensure_directory(templates_dir)
        ensure_directory(admin_panel_templates)
        
        # Pages to create
        pages = [
            'login.html',
            'register.html',
            'admin_panel.html',
            'channels_list.html',
            'categories_list.html',
            'messages_list.html',
            'sessions_list.html'
        ]
        
        for page in pages:
            target_file = admin_panel_templates / page
            
            # Skip if file exists
            if target_file.exists():
                continue
            
            # Create minimal template
            with open(target_file, 'w', encoding='utf-8') as f:
                f.write(f"""{% extends "base.html" %}

{% block title %}{page.replace('.html', '').replace('_', ' ').title()}{% endblock %}

{% block content %}
<div class="container mt-5">
    <div class="card">
        <div class="card-header bg-primary text-white">
            <h4 class="mb-0">{page.replace('.html', '').replace('_', ' ').title()}</h4>
        </div>
        <div class="card-body">
            <p>This is a placeholder template for {page}.</p>
        </div>
    </div>
</div>
{% endblock %}""")
            logger.info(f"Created placeholder template for {page}")
        
        return True
    except Exception as e:
        logger.error(f"Error creating placeholder templates: {e}")
        return False

def fix_urls():
    """Update URL configuration to handle all required paths"""
    try:
        # Check core/urls.py
        urls_file = Path('core/urls.py')
        if not urls_file.exists():
            logger.warning(f"URLs file not found at {urls_file}")
            return False
        
        with open(urls_file, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Check if accounts/login redirect is already there
        if "path('accounts/login/" in content:
            logger.info("Accounts login URL already configured")
        else:
            # Add accounts/login redirect
            accounts_login_code = """
    # Add Django auth URLs
    path('accounts/login/', lambda r: HttpResponse("Login", status=302, headers={"Location": "/admin_panel/login/"})),
    path('accounts/logout/', lambda r: HttpResponse("Logout", status=302, headers={"Location": "/admin_panel/logout/"})),"""
            
            # Insert before the last ']' of urlpatterns
            last_bracket = content.rfind(']', 0, content.find('# Static files handling'))
            if last_bracket > 0:
                new_content = content[:last_bracket] + accounts_login_code + content[last_bracket:]
                
                # Save updated file
                with open(urls_file, 'w', encoding='utf-8') as f:
                    f.write(new_content)
                
                logger.info("Updated core/urls.py with accounts login redirect")
            else:
                logger.warning("Could not locate urlpatterns in core/urls.py, manual fix required")
        
        return True
    except Exception as e:
        logger.error(f"Error fixing URLs: {e}")
        return False

def restart_services():
    """Restart services to apply changes"""
    try:
        # Create restart trigger file for Railway
        restart_file = 'railway_restart_trigger.txt'
        with open(restart_file, 'w') as f:
            f.write(f"Restart triggered at {django.utils.timezone.now()}\n")
        
        logger.info(f"Created restart trigger file: {restart_file}")
        
        # Touch wsgi.py to trigger code reload
        wsgi_file = os.path.join('core', 'wsgi.py')
        if os.path.exists(wsgi_file):
            with open(wsgi_file, 'a') as f:
                f.write(f'\n# Restart trigger: {django.utils.timezone.now()}')
            logger.info(f"Updated {wsgi_file} timestamp")
        
        # Try to restart the bot
        try:
            # Check if we're on Railway
            if os.environ.get('RAILWAY_SERVICE_NAME'):
                # In Railway environment, we use subprocess
                subprocess.run([sys.executable, 'direct_start_bot.py'], 
                               stdout=subprocess.PIPE, 
                               stderr=subprocess.PIPE)
                logger.info("Restarted bot using direct_start_bot.py")
            else:
                # In local environment
                if os.path.exists('emergency_fix.sh'):
                    # Unix environment
                    subprocess.run(['bash', 'emergency_fix.sh'], 
                                 stdout=subprocess.PIPE, 
                                 stderr=subprocess.PIPE)
                    logger.info("Restarted bot using emergency_fix.sh")
                elif os.path.exists('emergency_fix.bat'):
                    # Windows environment
                    subprocess.run(['emergency_fix.bat'], 
                                 stdout=subprocess.PIPE, 
                                 stderr=subprocess.PIPE)
                    logger.info("Restarted bot using emergency_fix.bat")
        except Exception as e:
            logger.error(f"Error restarting bot: {e}")
        
        return True
    except Exception as e:
        logger.error(f"Error restarting services: {e}")
        return False

def main():
    """Main function to run all fixes"""
    logger.info("=== Starting template and aiohttp session fixes ===")
    
    # Set up Django
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
    try:
        django.setup()
    except Exception as e:
        logger.error(f"Error setting up Django: {e}")
    
    # Run fixes
    check_templates()
    create_placeholder_templates()
    fix_urls()
    fix_aiohttp_sessions()
    apply_migrations()
    restart_services()
    
    logger.info("=== Fix completed ===")
    return True

if __name__ == "__main__":
    main() 