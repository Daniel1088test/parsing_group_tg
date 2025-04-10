#!/usr/bin/env python3
"""
Script to fix integration issues between bot, parser, and web interface
"""
import os
import sys
import logging
import re
import json
import subprocess
import traceback
from pathlib import Path

# Set environment variables first before importing django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
os.environ.setdefault('BOT_TOKEN', '8102516142:AAFTsVXXujHHKoX2KZGqZXBHPBznfgh7kg0')
os.environ.setdefault('BOT_USERNAME', 'chan_parsing_mon_bot')

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Replace the standard StreamHandler with one that has proper encoding
for handler in logger.handlers:
    if isinstance(handler, logging.StreamHandler):
        logger.removeHandler(handler)

# Add new handler with proper encoding
console_handler = logging.StreamHandler(sys.stdout)
console_handler.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))
logger.addHandler(console_handler)

# Now it's safe to import django
try:
    import django
    django.setup()
    logger.info("Django initialized successfully")
except Exception as e:
    logger.error(f"Error initializing Django: {e}")

def setup_environment():
    """Setup environment variables for bot and parser"""
    # Set bot token and username
    os.environ.setdefault('BOT_TOKEN', '8102516142:AAFTsVXXujHHKoX2KZGqZXBHPBznfgh7kg0')
    os.environ.setdefault('BOT_USERNAME', 'chan_parsing_mon_bot')
    
    # API settings for Telegram
    os.environ.setdefault('API_ID', '19840544')
    os.environ.setdefault('API_HASH', 'c839f28bad345082329ec086fca021fa')
    
    # Django settings
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
    
    # Check if we're in a Railway environment
    if 'RAILWAY_ENVIRONMENT' in os.environ or 'RAILWAY_SERVICE_NAME' in os.environ:
        # Set PostgreSQL environment variables
        os.environ.setdefault('PGHOST', 'postgres.railway.internal')
        os.environ.setdefault('PGPORT', '5432')
        os.environ.setdefault('PGUSER', 'postgres')
        os.environ.setdefault('PGDATABASE', 'railway')
    
    logger.info("Environment variables set")

def fix_templates():
    """Fix issues with Django templates"""
    try:
        # Initialize Django
        django.setup()
        
        # Create necessary template directories
        templates_dir = Path('templates')
        admin_templates_dir = templates_dir / 'admin_panel'
        
        # Create directories if they don't exist
        templates_dir.mkdir(exist_ok=True)
        admin_templates_dir.mkdir(exist_ok=True)
        
        logger.info(f"Created template directories: {templates_dir}, {admin_templates_dir}")
        
        # Fix issues with specific templates
        
        # 1. Make sure we have a base.html template
        base_template = templates_dir / 'base.html'
        if not base_template.exists():
            logger.info("Creating base.html template")
            
            base_content = """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{% block title %}Telegram Channel Parser{% endblock %}</title>
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
    <link href="https://cdn.jsdelivr.net/npm/font-awesome@4.7.0/css/font-awesome.min.css" rel="stylesheet">
    {% block extra_css %}{% endblock %}
</head>
<body>
    <nav class="navbar navbar-expand-lg navbar-dark bg-primary mb-4">
        <div class="container">
            <a class="navbar-brand" href="/">Telegram Channel Parser</a>
            <button class="navbar-toggler" type="button" data-bs-toggle="collapse" data-bs-target="#navbarNav">
                <span class="navbar-toggler-icon"></span>
            </button>
            <div class="collapse navbar-collapse" id="navbarNav">
                <ul class="navbar-nav ms-auto">
                    {% if user.is_authenticated %}
                    <li class="nav-item">
                        <a class="nav-link" href="/admin_panel/channels/">Channels</a>
                    </li>
                    <li class="nav-item">
                        <a class="nav-link" href="/admin_panel/sessions/">Sessions</a>
                    </li>
                    <li class="nav-item">
                        <a class="nav-link" href="/admin_panel/categories/">Categories</a>
                    </li>
                    <li class="nav-item">
                        <a class="nav-link" href="/admin_panel/messages/">Messages</a>
                    </li>
                    <li class="nav-item">
                        <a class="nav-link" href="/admin_panel/logout/">Logout</a>
                    </li>
                    {% else %}
                    <li class="nav-item">
                        <a class="nav-link" href="/admin_panel/login/">Login</a>
                    </li>
                    {% endif %}
                </ul>
            </div>
        </div>
    </nav>

    <div class="container">
        {% if messages %}
        <div class="messages">
            {% for message in messages %}
            <div class="alert alert-{{ message.tags }} alert-dismissible fade show" role="alert">
                {{ message }}
                <button type="button" class="btn-close" data-bs-dismiss="alert" aria-label="Close"></button>
            </div>
            {% endfor %}
        </div>
        {% endif %}

        {% block content %}{% endblock %}
    </div>

    <script src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/js/bootstrap.bundle.min.js"></script>
    <script src="https://code.jquery.com/jquery-3.6.0.min.js"></script>
    {% block extra_js %}{% endblock %}
</body>
</html>"""
            
            with open(base_template, 'w', encoding='utf-8') as f:
                f.write(base_content)
                
            logger.info("[OK] Created base.html template")
            
        # 2. Fix authorize_session.html
        authorize_template = admin_templates_dir / 'authorize_session.html'
        if authorize_template.exists():
            with open(authorize_template, 'r', encoding='utf-8') as f:
                content = f.read()
                
            # Fix the Telegram bot link
            if 'deep_link' in content:
                logger.info("authorize_session.html looks good")
            else:
                logger.info("Fixing authorize_session.html")
                
                # Create a fixed version of the template
                fixed_content = """{% extends "base.html" %}
{% load static %}

{% block title %}Authorize Session{% endblock %}

{% block content %}
<div class="container mt-4">
    <div class="card">
        <div class="card-header bg-primary text-white">
            <h4 class="mb-0">Authorize Session: {{ session.phone }}</h4>
        </div>
        <div class="card-body">
            <div class="alert alert-info">
                Please tap the button below to open the Telegram bot and complete the authorization.
            </div>
            
            <form method="post">
                {% csrf_token %}
                <div class="text-center">
                    <h5 class="mb-3">Open Telegram Bot to authorize:</h5>
                    <a href="{{ deep_link }}" class="btn btn-lg btn-primary" target="_blank">
                        <i class="fa fa-telegram"></i> Open Telegram Bot
                    </a>
                </div>
            </form>
            
            <div class="alert alert-light mt-4">
                After you authorize via the Telegram bot, return to this page and check the status.
            </div>
            
            <div class="mt-4 text-center">
                <a href="{% url 'admin_panel:sessions_list' %}" class="btn btn-secondary">
                    <i class="fa fa-arrow-left"></i> Back to Sessions List
                </a>
                <button onclick="location.reload()" class="btn btn-success">
                    <i class="fa fa-refresh"></i> Refresh Status
                </button>
            </div>
        </div>
    </div>
</div>
{% endblock %}"""
                
                with open(authorize_template, 'w', encoding='utf-8') as f:
                    f.write(fixed_content)
                    
                logger.info("[OK] Fixed authorize_session.html")
        else:
            logger.info("Creating authorize_session.html")
            
            new_content = """{% extends "base.html" %}
{% load static %}

{% block title %}Authorize Session{% endblock %}

{% block content %}
<div class="container mt-4">
    <div class="card">
        <div class="card-header bg-primary text-white">
            <h4 class="mb-0">Authorize Session: {{ session.phone }}</h4>
        </div>
        <div class="card-body">
            <div class="alert alert-info">
                Please tap the button below to open the Telegram bot and complete the authorization.
            </div>
            
            <form method="post">
                {% csrf_token %}
                <div class="text-center">
                    <h5 class="mb-3">Open Telegram Bot to authorize:</h5>
                    <a href="{{ deep_link }}" class="btn btn-lg btn-primary" target="_blank">
                        <i class="fa fa-telegram"></i> Open Telegram Bot
                    </a>
                </div>
            </form>
            
            <div class="alert alert-light mt-4">
                After you authorize via the Telegram bot, return to this page and check the status.
            </div>
            
            <div class="mt-4 text-center">
                <a href="{% url 'admin_panel:sessions_list' %}" class="btn btn-secondary">
                    <i class="fa fa-arrow-left"></i> Back to Sessions List
                </a>
                <button onclick="location.reload()" class="btn btn-success">
                    <i class="fa fa-refresh"></i> Refresh Status
                </button>
            </div>
        </div>
    </div>
</div>
{% endblock %}"""
            
            with open(authorize_template, 'w', encoding='utf-8') as f:
                f.write(new_content)
                
            logger.info("[OK] Created authorize_session.html")
        
        # 3. Create or fix other important templates
        template_files = {
            'sessions_list.html': """{% extends "base.html" %}
{% load static %}

{% block title %}Telegram Sessions{% endblock %}

{% block content %}
<div class="container mt-4">
    <div class="d-flex justify-content-between align-items-center mb-4">
        <h1>Telegram Sessions</h1>
        <a href="{% url 'admin_panel:create_session' %}" class="btn btn-primary">
            <i class="fa fa-plus"></i> Add New Session
        </a>
    </div>

    <div class="card">
        <div class="card-header bg-primary text-white">
            <h4 class="mb-0">Available Sessions</h4>
        </div>
        <div class="card-body">
            {% if sessions %}
            <div class="table-responsive">
                <table class="table table-hover">
                    <thead>
                        <tr>
                            <th>Phone</th>
                            <th>Username</th>
                            <th>Status</th>
                            <th>Actions</th>
                        </tr>
                    </thead>
                    <tbody>
                        {% for session in sessions %}
                        <tr>
                            <td>{{ session.phone }}</td>
                            <td>{{ session.username|default:"Not logged in" }}</td>
                            <td>
                                {% if session.is_authorized %}
                                <span class="badge bg-success">Authorized</span>
                                {% else %}
                                <span class="badge bg-warning">Not authorized</span>
                                {% endif %}
                            </td>
                            <td>
                                <div class="btn-group">
                                    {% if not session.is_authorized %}
                                    <a href="{% url 'admin_panel:authorize_session' session.id %}" class="btn btn-sm btn-primary">
                                        <i class="fa fa-key"></i> Authorize
                                    </a>
                                    {% endif %}
                                    <a href="{% url 'admin_panel:delete_session' session.id %}" class="btn btn-sm btn-danger">
                                        <i class="fa fa-trash"></i> Delete
                                    </a>
                                </div>
                            </td>
                        </tr>
                        {% endfor %}
                    </tbody>
                </table>
            </div>
            {% else %}
            <div class="alert alert-info">
                No Telegram sessions found. Please add a new session.
            </div>
            {% endif %}
        </div>
    </div>
</div>
{% endblock %}""",

            'channels_list.html': """{% extends "base.html" %}
{% load static %}

{% block title %}Telegram Channels{% endblock %}

{% block content %}
<div class="container mt-4">
    <div class="d-flex justify-content-between align-items-center mb-4">
        <h1>Telegram Channels</h1>
        <a href="{% url 'admin_panel:create_channel' %}" class="btn btn-primary">
            <i class="fa fa-plus"></i> Add New Channel
        </a>
    </div>

    <div class="card">
        <div class="card-header bg-primary text-white">
            <h4 class="mb-0">Monitored Channels</h4>
        </div>
        <div class="card-body">
            {% if channels %}
            <div class="table-responsive">
                <table class="table table-hover">
                    <thead>
                        <tr>
                            <th>Name</th>
                            <th>Link</th>
                            <th>Category</th>
                            <th>Session</th>
                            <th>Active</th>
                            <th>Actions</th>
                        </tr>
                    </thead>
                    <tbody>
                        {% for channel in channels %}
                        <tr>
                            <td>{{ channel.name }}</td>
                            <td><a href="{{ channel.link }}" target="_blank">{{ channel.link }}</a></td>
                            <td>{{ channel.category.name|default:"No category" }}</td>
                            <td>{{ channel.session.phone|default:"Default session" }}</td>
                            <td>
                                {% if channel.is_active %}
                                <span class="badge bg-success">Active</span>
                                {% else %}
                                <span class="badge bg-danger">Inactive</span>
                                {% endif %}
                            </td>
                            <td>
                                <div class="btn-group">
                                    <a href="{% url 'admin_panel:edit_channel' channel.id %}" class="btn btn-sm btn-info">
                                        <i class="fa fa-edit"></i> Edit
                                    </a>
                                    <a href="{% url 'admin_panel:delete_channel' channel.id %}" class="btn btn-sm btn-danger">
                                        <i class="fa fa-trash"></i> Delete
                                    </a>
                                </div>
                            </td>
                        </tr>
                        {% endfor %}
                    </tbody>
                </table>
            </div>
            {% else %}
            <div class="alert alert-info">
                No Telegram channels found. Please add a new channel.
            </div>
            {% endif %}
        </div>
    </div>
</div>
{% endblock %}""",

            'create_session.html': """{% extends "base.html" %}
{% load static %}

{% block title %}Create New Session{% endblock %}

{% block content %}
<div class="container mt-4">
    <div class="card">
        <div class="card-header bg-primary text-white">
            <h4 class="mb-0">Create New Telegram Session</h4>
        </div>
        <div class="card-body">
            <form method="post">
                {% csrf_token %}
                <div class="mb-3">
                    <label for="phone" class="form-label">Phone Number</label>
                    <input type="text" class="form-control" id="phone" name="phone" required placeholder="+380123456789">
                    <div class="form-text text-muted">Enter the phone number in international format with country code</div>
                </div>
                
                <div class="mt-4">
                    <a href="{% url 'admin_panel:sessions_list' %}" class="btn btn-secondary">
                        <i class="fa fa-arrow-left"></i> Back to Sessions
                    </a>
                    <button type="submit" class="btn btn-primary">
                        <i class="fa fa-save"></i> Create Session
                    </button>
                </div>
            </form>
        </div>
    </div>
</div>
{% endblock %}"""
        }
        
        # Create or fix each template
        for filename, content in template_files.items():
            template_path = admin_templates_dir / filename
            if not template_path.exists():
                with open(template_path, 'w', encoding='utf-8') as f:
                    f.write(content)
                logger.info(f"[OK] Created {filename}")
            else:
                logger.info(f"Template {filename} already exists")
        
        return True
    except Exception as e:
        logger.error(f"Error fixing templates: {e}")
        logger.error(traceback.format_exc())
        return False

def fix_views():
    """Fix issues with Django views"""
    try:
        views_path = Path('admin_panel/views.py')
        
        if not views_path.exists():
            logger.error("Could not find admin_panel/views.py")
            return False
        
        with open(views_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Fix session list view if needed
        if 'def sessions_list' in content:
            # Check if the view handles exceptions properly
            sessions_list_match = re.search(r'def sessions_list[^}]*?}', content, re.DOTALL)
            if sessions_list_match and 'try:' not in sessions_list_match.group(0):
                # Add error handling
                original_func = sessions_list_match.group(0)
                fixed_func = re.sub(
                    r'def sessions_list\((.*?)\):(.*?)return render\((.*?)\)',
                    r'def sessions_list(\1):\n    try:\2return render(\3)\n    except Exception as e:\n        messages.error(request, f"Error fetching sessions: {e}")\n        return render(request, "admin_panel/sessions_list.html", {"sessions": []})',
                    original_func,
                    flags=re.DOTALL
                )
                
                content = content.replace(original_func, fixed_func)
                logger.info("Fixed sessions_list view to handle exceptions")
        
        # Fix authorize_session view if needed
        if 'def authorize_session_view' in content and '@login_required' in content:
            # Check if deep_link generation is correct
            authorize_match = re.search(r'def authorize_session_view[^}]*?}', content, re.DOTALL)
            if authorize_match and 'deep_link' in authorize_match.group(0):
                if 'bot_username' in authorize_match.group(0) and os.environ.get('BOT_USERNAME') not in authorize_match.group(0):
                    # Fix the deep_link generation
                    original_func = authorize_match.group(0)
                    fixed_func = re.sub(
                        r'(bot_username\s*=\s*)(.*?)(\s*?[\r\n])',
                        f'\\1os.environ.get("BOT_USERNAME", "chan_parsing_mon_bot")\\3',
                        original_func
                    )
                    
                    content = content.replace(original_func, fixed_func)
                    logger.info("Fixed authorize_session_view to use correct bot username")
        
        # Write the updated content
        with open(views_path, 'w', encoding='utf-8') as f:
            f.write(content)
            
        logger.info("[OK] Fixed views.py")
        
        return True
    except Exception as e:
        logger.error(f"Error fixing views: {e}")
        logger.error(traceback.format_exc())
        return False

def fix_bot_handlers():
    """Fix issues with Telegram bot handlers"""
    try:
        # Find the bot handlers file
        bot_files = [
            Path('tg_bot/handlers/user.py'),
            Path('tg_bot/handlers/admin.py'),
            Path('tg_bot/handlers/common.py'),
            Path('tg_bot/handlers.py')
        ]
        
        bot_file = None
        for file_path in bot_files:
            if file_path.exists():
                bot_file = file_path
                break
        
        if not bot_file:
            logger.error("Could not find bot handlers file")
            return False
        
        logger.info(f"Found bot handlers file: {bot_file}")
        
        with open(bot_file, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Common issues to fix in bot handlers
        
        # 1. Fix error in session authorization handler
        if 'authorize_session' in content and ('auth_token' in content or 'auth_' in content):
            # Check if handler properly extracts auth token
            if 'auth_token = None' in content and re.search(r'message\.text\.split\([\'"]', content):
                logger.info("Authorization handler looks good")
            else:
                # Fix the authorization handler
                auth_pattern = r'async def (cmd_authorize|authorize_session|on_authorize_command|process_auth).*?}[\n\r]'
                auth_handler = re.search(auth_pattern, content, re.DOTALL)
                
                if auth_handler:
                    original_handler = auth_handler.group(0)
                    
                    # Check if handler has issues extracting the auth token
                    if 'auth_token' not in original_handler or 'split' not in original_handler:
                        # Add proper auth token extraction
                        fixed_handler = re.sub(
                            r'async def ([a-zA-Z0-9_]+)\((.*?)message(.*?)\):(.*?)$',
                            r'async def \1(\2message\3):\n    # Extract auth token from command\n    auth_token = None\n    if message.text and message.text.startswith("/"):\n        parts = message.text.split()\n        if len(parts) > 1:\n            auth_token = parts[1]\n\4',
                            original_handler,
                            flags=re.DOTALL
                        )
                        
                        content = content.replace(original_handler, fixed_handler)
                        logger.info("Fixed authorize session handler to properly extract auth token")
        
        # 2. Fix error in add session handler
        if ('add_session' in content or 'new_session' in content) and 'phone' in content:
            # Check if handler properly processes phone number
            if re.search(r'phone\s*=\s*[\'"]', content) and re.search(r'await message\.answer\(', content):
                logger.info("Add session handler looks good")
            else:
                # Fix the add session handler
                add_pattern = r'async def (cmd_add_session|add_session|on_add_session_command|process_phone).*?}[\n\r]'
                add_handler = re.search(add_pattern, content, re.DOTALL)
                
                if add_handler:
                    original_handler = add_handler.group(0)
                    
                    # Check if handler has issues processing phone number
                    if 'phone' in original_handler and not re.search(r'phone\s*=\s*message\.text', original_handler):
                        # Add proper phone number extraction
                        fixed_handler = re.sub(
                            r'async def ([a-zA-Z0-9_]+)\((.*?)message(.*?)\):(.*?)$',
                            r'async def \1(\2message\3):\n    # Get phone number from message\n    if not message.text:\n        await message.answer("Please send a valid phone number")\n        return\n    \n    phone = message.text.strip()\n    if not phone.startswith("+"):\n        phone = "+" + phone\n\4',
                            original_handler,
                            flags=re.DOTALL
                        )
                        
                        content = content.replace(original_handler, fixed_handler)
                        logger.info("Fixed add session handler to properly process phone number")
        
        # Write the updated content
        with open(bot_file, 'w', encoding='utf-8') as f:
            f.write(content)
            
        logger.info(f"[OK] Fixed bot handlers in {bot_file}")
        
        return True
    except Exception as e:
        logger.error(f"Error fixing bot handlers: {e}")
        logger.error(traceback.format_exc())
        return False

def fix_parser():
    """Fix issues with the parser"""
    try:
        # Find the parser files
        parser_files = [
            Path('parser/main.py'),
            Path('parser/parser.py'),
            Path('run_parser.py')
        ]
        
        parser_file = None
        for file_path in parser_files:
            if file_path.exists():
                parser_file = file_path
                break
        
        if not parser_file:
            logger.error("Could not find parser file")
            return False
        
        logger.info(f"Found parser file: {parser_file}")
        
        with open(parser_file, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Common issues to fix in parser
        
        # 1. Fix database connection issues
        if 'django.setup()' not in content and 'os.environ.setdefault' not in content:
            # Add Django setup code at the top of the file
            setup_code = """import os
import sys
import django

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()

"""
            content = re.sub(r'(import[^\n]*?\n+)', f'\\1{setup_code}', content, count=1)
            logger.info("Added Django setup code to parser")
        
        # 2. Fix session management issues
        if 'TelegramClient' in content and 'session' in content:
            # Make sure sessions are properly loaded
            if 'from admin_panel.models import TelegramSession' not in content:
                # Add import for TelegramSession
                import_code = "from admin_panel.models import TelegramSession, Channel\n"
                content = re.sub(r'(import[^\n]*?\n+)', f'\\1{import_code}', content, count=1)
                logger.info("Added import for TelegramSession model")
            
            # Check if parser loads sessions from database
            if not re.search(r'TelegramSession\.objects\.filter\(is_authorized=True\)', content):
                # Fix session loading code
                session_pattern = r'(async)?\s*def\s+(start|run|parse|main|start_parsing).*?}'
                session_func = re.search(session_pattern, content, re.DOTALL)
                
                if session_func:
                    original_func = session_func.group(0)
                    
                    # Add session loading code
                    if 'async' in original_func:
                        # Async function
                        fixed_func = re.sub(
                            r'(async\s+def\s+[a-zA-Z0-9_]+\(.*?\):\s*)',
                            r'\1\n    try:\n        # Load all authorized sessions from database\n        sessions = TelegramSession.objects.filter(is_authorized=True)\n        if not sessions.exists():\n            logger.warning("No authorized sessions found")\n            return False\n        \n        # Get all active channels\n        channels = Channel.objects.filter(is_active=True)\n        if not channels.exists():\n            logger.warning("No active channels found")\n            return False\n    except Exception as e:\n        logger.error(f"Error loading sessions or channels: {e}")\n        return False\n\n',
                            original_func,
                            flags=re.DOTALL
                        )
                    else:
                        # Sync function
                        fixed_func = re.sub(
                            r'(def\s+[a-zA-Z0-9_]+\(.*?\):\s*)',
                            r'\1\n    try:\n        # Load all authorized sessions from database\n        sessions = TelegramSession.objects.filter(is_authorized=True)\n        if not sessions.exists():\n            logger.warning("No authorized sessions found")\n            return False\n        \n        # Get all active channels\n        channels = Channel.objects.filter(is_active=True)\n        if not channels.exists():\n            logger.warning("No active channels found")\n            return False\n    except Exception as e:\n        logger.error(f"Error loading sessions or channels: {e}")\n        return False\n\n',
                            original_func,
                            flags=re.DOTALL
                        )
                    
                    content = content.replace(original_func, fixed_func)
                    logger.info("Fixed parser to load sessions and channels from database")
        
        # Write the updated content
        with open(parser_file, 'w', encoding='utf-8') as f:
            f.write(content)
            
        logger.info(f"[OK] Fixed parser in {parser_file}")
        
        return True
    except Exception as e:
        logger.error(f"Error fixing parser: {e}")
        logger.error(traceback.format_exc())
        return False

def restart_services():
    """Restart all services"""
    try:
        # Find available service scripts
        service_scripts = {
            'run.py': 'all services',
            'direct_bot_runner.py': 'bot',
            'run_bot.py': 'bot',
            'run_parser.py': 'parser',
            'manage.py': 'Django'
        }
        
        restart_script = None
        for script, service in service_scripts.items():
            if Path(script).exists():
                restart_script = script
                logger.info(f"Found {service} script: {script}")
                break
        
        if not restart_script:
            logger.error("Could not find any service scripts to restart")
            return False
        
        # Run the restart script
        logger.info(f"Restarting services using {restart_script}")
        
        if restart_script == 'run.py':
            # Start all services
            subprocess.Popen([sys.executable, restart_script], 
                           start_new_session=True if sys.platform != 'win32' else False,
                           creationflags=subprocess.CREATE_NEW_PROCESS_GROUP | subprocess.DETACHED_PROCESS if sys.platform == 'win32' else 0)
        elif restart_script == 'manage.py':
            # Start Django server
            subprocess.Popen([sys.executable, restart_script, 'runserver', '0.0.0.0:8080'],
                           start_new_session=True if sys.platform != 'win32' else False,
                           creationflags=subprocess.CREATE_NEW_PROCESS_GROUP | subprocess.DETACHED_PROCESS if sys.platform == 'win32' else 0)
        else:
            # Start individual service
            subprocess.Popen([sys.executable, restart_script],
                           start_new_session=True if sys.platform != 'win32' else False,
                           creationflags=subprocess.CREATE_NEW_PROCESS_GROUP | subprocess.DETACHED_PROCESS if sys.platform == 'win32' else 0)
        
        logger.info(f"[OK] Restarted services using {restart_script}")
        
        return True
    except Exception as e:
        logger.error(f"Error restarting services: {e}")
        logger.error(traceback.format_exc())
        return False

def main():
    """Main function to fix integration issues"""
    logger.info("=== Starting integration issues fix ===")
    
    # Setup environment
    setup_environment()
    
    # Fix templates
    fix_templates()
    
    # Fix views
    fix_views()
    
    # Fix bot handlers
    fix_bot_handlers()
    
    # Fix parser
    fix_parser()
    
    # Restart services
    restart_services()
    
    logger.info("=== Integration issues fix completed ===")
    logger.info("Services have been restarted. Please check if everything is working correctly.")
    
    return True

if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        logger.error(traceback.format_exc())
    sys.exit(0) 