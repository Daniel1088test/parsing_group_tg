#!/usr/bin/env python3
"""
Master script to fix all issues with the application
"""
import os
import sys
import logging
import traceback
import re
import json
import subprocess
import time
from pathlib import Path

# Set environment variables first
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
os.environ.setdefault('BOT_TOKEN', '8102516142:AAFTsVXXujHHKoX2KZGqZXBHPBznfgh7kg0')
os.environ.setdefault('BOT_USERNAME', 'chan_parsing_mon_bot')
os.environ.setdefault('API_ID', '19840544')
os.environ.setdefault('API_HASH', 'c839f28bad345082329ec086fca021fa')

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('fix_all_issues.log', encoding='utf-8'),
    ]
)
logger = logging.getLogger(__name__)

# Add console handler with proper encoding
console_handler = logging.StreamHandler(sys.stdout)
console_handler.setLevel(logging.INFO)
console_handler.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))
logger.addHandler(console_handler)

# Safe import of django
try:
    import django
    import psycopg2
    django.setup()
    logger.info("[OK] Django initialized successfully")
except Exception as e:
    logger.error(f"Error initializing Django: {e}")
    logger.error(traceback.format_exc())

def kill_existing_processes():
    """Kill any existing bot, parser, or Django processes"""
    try:
        # Find and kill Python processes
        if sys.platform == "win32":
            # Windows
            subprocess.run(["taskkill", "/F", "/IM", "python.exe", "/T"], 
                           stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            logger.info("Killed any existing Python processes on Windows")
        else:
            # Unix-like
            subprocess.run(["pkill", "-f", "python"], 
                           stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            logger.info("Killed any existing Python processes on Unix")
            
        # Wait a moment for processes to terminate
        time.sleep(2)
        
        return True
    except Exception as e:
        logger.error(f"Error killing existing processes: {e}")
        return False

def fix_database_issues():
    """Fix database connection and model issues"""
    try:
        # Get Django settings
        from django.conf import settings
        
        # Set the correct database engine
        if os.environ.get('RAILWAY_SERVICE_NAME'):
            # Railway environment with PostgreSQL
            db_settings = {
                'ENGINE': 'django.db.backends.postgresql',
                'NAME': os.environ.get('PGDATABASE', 'railway'),
                'USER': os.environ.get('PGUSER', 'postgres'),
                'PASSWORD': os.environ.get('PGPASSWORD', ''),
                'HOST': os.environ.get('PGHOST', 'postgres.railway.internal'),
                'PORT': os.environ.get('PGPORT', '5432'),
            }
        else:
            # Local development - try to use SQLite if PostgreSQL is not available
            try:
                # Test PostgreSQL connection
                conn = psycopg2.connect(
                    host=os.environ.get('PGHOST', 'localhost'),
                    port=os.environ.get('PGPORT', '5432'),
                    user=os.environ.get('PGUSER', 'postgres'),
                    password=os.environ.get('PGPASSWORD', ''),
                    database=os.environ.get('PGDATABASE', 'postgres')
                )
                conn.close()
                
                # PostgreSQL is available
                db_settings = {
                    'ENGINE': 'django.db.backends.postgresql',
                    'NAME': os.environ.get('PGDATABASE', 'postgres'),
                    'USER': os.environ.get('PGUSER', 'postgres'),
                    'PASSWORD': os.environ.get('PGPASSWORD', ''),
                    'HOST': os.environ.get('PGHOST', 'localhost'),
                    'PORT': os.environ.get('PGPORT', '5432'),
                }
                logger.info("Using PostgreSQL database")
            except:
                # Fall back to SQLite
                db_path = os.path.join(settings.BASE_DIR, 'db.sqlite3')
                db_settings = {
                    'ENGINE': 'django.db.backends.sqlite3',
                    'NAME': db_path,
                }
                logger.info(f"Using SQLite database at {db_path}")
        
        # Update settings.py with the correct database settings
        settings_path = os.path.join('core', 'settings.py')
        
        if not os.path.exists(settings_path):
            logger.error(f"Settings file not found at {settings_path}")
            return False
            
        with open(settings_path, 'r', encoding='utf-8') as f:
            content = f.read()
            
        # Update DATABASE settings
        db_str = json.dumps(db_settings, indent=4).replace('"', "'")
        db_str = db_str.replace("'ENGINE'", "'ENGINE'").replace("'NAME'", "'NAME'")
        
        # Replace existing DATABASES setting
        if 'DATABASES' in content:
            content = re.sub(
                r'DATABASES\s*=\s*\{[^}]*\}',
                f'DATABASES = {{\n    "default": {db_str}\n}}',
                content
            )
            logger.info("Updated DATABASES setting in settings.py")
        
        # Add TELEGRAM_API_TOKEN if not present
        if 'TELEGRAM_API_TOKEN' not in content:
            # Find a good insertion point
            if '# Application definition' in content:
                content = content.replace(
                    '# Application definition',
                    f'# Telegram API Token\nTELEGRAM_API_TOKEN = os.environ.get("BOT_TOKEN", "8102516142:AAFTsVXXujHHKoX2KZGqZXBHPBznfgh7kg0")\n\n# Application definition'
                )
            else:
                # Add at the end
                content += '\n# Telegram API Token\nTELEGRAM_API_TOKEN = os.environ.get("BOT_TOKEN", "8102516142:AAFTsVXXujHHKoX2KZGqZXBHPBznfgh7kg0")\n'
            
            logger.info("Added TELEGRAM_API_TOKEN to settings.py")
        
        # Write updated content
        with open(settings_path, 'w', encoding='utf-8') as f:
            f.write(content)
        
        # Update or create .env file with database settings
        env_path = '.env'
        env_content = []
        
        if os.path.exists(env_path):
            with open(env_path, 'r', encoding='utf-8') as f:
                env_content = f.readlines()
        
        # Update or add environment variables
        env_vars = {
            'BOT_TOKEN': '8102516142:AAFTsVXXujHHKoX2KZGqZXBHPBznfgh7kg0',
            'BOT_USERNAME': 'chan_parsing_mon_bot',
            'API_ID': '19840544',
            'API_HASH': 'c839f28bad345082329ec086fca021fa',
            'DJANGO_SETTINGS_MODULE': 'core.settings',
        }
        
        # Add database settings if using PostgreSQL
        if db_settings['ENGINE'] == 'django.db.backends.postgresql':
            env_vars.update({
                'PGDATABASE': db_settings['NAME'],
                'PGUSER': db_settings['USER'],
                'PGHOST': db_settings['HOST'],
                'PGPORT': db_settings['PORT'],
            })
            
            # Add password if provided
            if db_settings.get('PASSWORD'):
                env_vars['PGPASSWORD'] = db_settings['PASSWORD']
        
        # Process existing lines
        new_env_content = []
        
        # Track which variables we've processed
        processed_vars = set()
        
        # Update existing variables
        for line in env_content:
            line = line.strip()
            if not line or line.startswith('#'):
                new_env_content.append(line)
                continue
                
            # Check if this is an environment variable
            if '=' in line:
                key, _ = line.split('=', 1)
                key = key.strip()
                
                if key in env_vars:
                    new_env_content.append(f"{key}={env_vars[key]}")
                    processed_vars.add(key)
                else:
                    new_env_content.append(line)
        
        # Add any missing variables
        for key, value in env_vars.items():
            if key not in processed_vars:
                new_env_content.append(f"{key}={value}")
        
        # Write updated .env file
        with open(env_path, 'w', encoding='utf-8') as f:
            for line in new_env_content:
                f.write(f"{line}\n")
                
        logger.info(f"Updated {env_path} with correct environment variables")
        
        # Fix models if needed
        try:
            # Fix non-nullable fields that should be nullable
            models_path = os.path.join('admin_panel', 'models.py')
            
            if os.path.exists(models_path):
                with open(models_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                # Fix 1: telegram_channel_id field
                if 'telegram_channel_id' in content and 'null=True' not in re.search(r'telegram_channel_id\s*=\s*models\.', content).group(0):
                    content = re.sub(
                        r'(telegram_channel_id\s*=\s*models\.[^,\)]+)',
                        r'\1, null=True, blank=True',
                        content
                    )
                    logger.info("Fixed telegram_channel_id field")
                
                # Fix 2: Other common fields that should be nullable
                for field in ['username', 'title', 'description', 'link', 'name']:
                    # Find field definition
                    field_match = re.search(rf'{field}\s*=\s*models\.Char[^,\)]+', content)
                    if field_match and 'null=True' not in field_match.group(0):
                        content = re.sub(
                            rf'({field}\s*=\s*models\.Char[^,\)]+)',
                            r'\1, null=True, blank=True',
                            content
                        )
                        logger.info(f"Fixed {field} field")
                
                # Fix 3: Make sure BotSettings.bot_token doesn't depend on settings.TELEGRAM_API_TOKEN
                if 'bot_token' in content and 'settings.TELEGRAM_API_TOKEN' in content:
                    content = re.sub(
                        r'(bot_token\s*=\s*models\.CharField\([^)]*default=)settings\.TELEGRAM_API_TOKEN([^)]*\))',
                        r'\1"8102516142:AAFTsVXXujHHKoX2KZGqZXBHPBznfgh7kg0"\2',
                        content
                    )
                    logger.info("Fixed bot_token field to not depend on settings.TELEGRAM_API_TOKEN")
                
                # Write updated content
                with open(models_path, 'w', encoding='utf-8') as f:
                    f.write(content)
                
                logger.info(f"Updated {models_path} with fixed fields")
        except Exception as e:
            logger.error(f"Error fixing model fields: {e}")
        
        # Apply migrations
        try:
            # Initialize Django
            from django.core.management import call_command
            
            # Make migrations
            logger.info("Running makemigrations...")
            call_command('makemigrations')
            
            # Apply migrations
            logger.info("Running migrate...")
            call_command('migrate')
            
            logger.info("[OK] Applied database migrations")
        except Exception as e:
            logger.error(f"Error applying migrations: {e}")
            logger.error(traceback.format_exc())
        
        return True
    except Exception as e:
        logger.error(f"Error fixing database issues: {e}")
        logger.error(traceback.format_exc())
        return False

def fix_templates():
    """Fix issues with Django templates"""
    try:
        # Create template directories
        templates_dir = Path('templates')
        admin_templates_dir = templates_dir / 'admin_panel'
        
        templates_dir.mkdir(exist_ok=True)
        admin_templates_dir.mkdir(exist_ok=True)
        logger.info(f"Created template directories: {templates_dir}, {admin_templates_dir}")
        
        # Create base.html template if it doesn't exist
        base_template = templates_dir / 'base.html'
        if not base_template.exists():
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
            
            logger.info(f"Created base.html template")
        
        # Create or fix important templates
        template_files = {
            'authorize_session.html': """{% extends "base.html" %}
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
{% endblock %}""",
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
        
        # Create or update templates
        for filename, content in template_files.items():
            template_path = admin_templates_dir / filename
            if not template_path.exists():
                with open(template_path, 'w', encoding='utf-8') as f:
                    f.write(content)
                logger.info(f"Created {filename}")
            else:
                # Check if template needs to be updated (e.g., missing deep_link)
                with open(template_path, 'r', encoding='utf-8') as f:
                    existing_content = f.read()
                
                if filename == 'authorize_session.html' and 'deep_link' not in existing_content:
                    with open(template_path, 'w', encoding='utf-8') as f:
                        f.write(content)
                    logger.info(f"Updated {filename} with deep_link support")
        
        return True
    except Exception as e:
        logger.error(f"Error fixing templates: {e}")
        logger.error(traceback.format_exc())
        return False

def fix_views():
    """Fix issues with Django views"""
    try:
        views_path = os.path.join('admin_panel', 'views.py')
        
        if not os.path.exists(views_path):
            logger.error(f"Views file not found: {views_path}")
            return False
        
        with open(views_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Fix session list view if needed
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
        
        # Fix authorize_session_view if needed
        authorize_match = re.search(r'def authorize_session_view[^}]*?}', content, re.DOTALL)
        if authorize_match and 'deep_link' in authorize_match.group(0):
            # Check if using environment variable for bot username
            if 'os.environ.get' not in authorize_match.group(0):
                # Fix the deep_link generation
                original_func = authorize_match.group(0)
                
                # Make sure we import os if needed
                if 'import os' not in content:
                    content = "import os\n" + content
                
                fixed_func = re.sub(
                    r'(bot_username\s*=\s*)([^=\n]*?)(\s*?[\r\n])',
                    r'\1os.environ.get("BOT_USERNAME", "chan_parsing_mon_bot")\3',
                    original_func
                )
                
                content = content.replace(original_func, fixed_func)
                logger.info("Fixed authorize_session_view to use environment variable for bot username")
        
        # Write the updated content
        with open(views_path, 'w', encoding='utf-8') as f:
            f.write(content)
        
        logger.info(f"[OK] Updated {views_path}")
        
        return True
    except Exception as e:
        logger.error(f"Error fixing views: {e}")
        logger.error(traceback.format_exc())
        return False

def fix_integration():
    """Fix integration between bot, parser, and web interface"""
    try:
        # Fix bot handlers
        bot_files = [
            Path('tg_bot/handlers/user.py'),
            Path('tg_bot/handlers/admin.py'),
            Path('tg_bot/handlers/common.py'),
            Path('tg_bot/handlers.py')
        ]
        
        for bot_file in bot_files:
            if bot_file.exists():
                logger.info(f"Checking bot handlers in {bot_file}")
                
                with open(bot_file, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                # Fix session authorization handler
                if 'authorize_session' in content:
                    auth_handler = re.search(r'async def (\w+_authorize\w*|authorize\w*|cmd_auth\w*).*?}', content, re.DOTALL)
                    if auth_handler and 'auth_token' not in auth_handler.group(0):
                        original_handler = auth_handler.group(0)
                        
                        # Add auth token extraction
                        fixed_handler = re.sub(
                            r'(async def \w+\(.*?\):)',
                            r'\1\n    # Extract auth token from command\n    auth_token = None\n    if message.text and len(message.text.split()) > 1:\n        auth_token = message.text.split()[1]',
                            original_handler
                        )
                        
                        content = content.replace(original_handler, fixed_handler)
                        logger.info(f"Fixed authorization handler in {bot_file}")
                
                # Fix add session handler
                if 'add_session' in content or 'new_session' in content:
                    add_handler = re.search(r'async def (\w+_add_session|add_session\w*|new_session\w*).*?}', content, re.DOTALL)
                    if add_handler and 'phone' in add_handler.group(0) and 'message.text' not in add_handler.group(0):
                        original_handler = add_handler.group(0)
                        
                        # Add phone extraction
                        fixed_handler = re.sub(
                            r'(async def \w+\(.*?\):)',
                            r'\1\n    # Get phone from message\n    if not message.text:\n        await message.answer("Please provide a valid phone number")\n        return\n    \n    phone = message.text.strip()\n    if not phone.startswith("+"):\n        phone = "+" + phone',
                            original_handler
                        )
                        
                        content = content.replace(original_handler, fixed_handler)
                        logger.info(f"Fixed add session handler in {bot_file}")
                
                # Update the file if changed
                with open(bot_file, 'w', encoding='utf-8') as f:
                    f.write(content)
        
        # Fix parser
        parser_files = [
            Path('parser/main.py'),
            Path('parser/parser.py'),
            Path('run_parser.py')
        ]
        
        for parser_file in parser_files:
            if parser_file.exists():
                logger.info(f"Checking parser in {parser_file}")
                
                with open(parser_file, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                # Ensure Django setup code is present
                if 'django.setup()' not in content:
                    setup_code = """
# Set up Django
import os
import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()
"""
                    # Find a good place to insert
                    if 'import' in content:
                        # After the imports
                        import_section = re.search(r'((?:^import .*?\n)+)', content, re.MULTILINE)
                        if import_section:
                            content = content.replace(import_section.group(0), import_section.group(0) + setup_code)
                        else:
                            # Just add to the top
                            content = setup_code + content
                    else:
                        # Just add to the top
                        content = setup_code + content
                    
                    logger.info(f"Added Django setup code to {parser_file}")
                
                # Make sure TelegramSession model is imported
                if 'from admin_panel.models import' not in content and ('TelegramSession' in content or 'Channel' in content):
                    import_code = """
from admin_panel.models import TelegramSession, Channel
"""
                    # Find a good place to insert
                    if 'import' in content:
                        # After the imports
                        last_import = re.search(r'^import .*?$', content, re.MULTILINE | re.DOTALL)
                        if last_import:
                            content = content.replace(last_import.group(0), last_import.group(0) + import_code)
                        else:
                            # Just add to the top
                            content = import_code + content
                    else:
                        # Just add to the top
                        content = import_code + content
                    
                    logger.info(f"Added model imports to {parser_file}")
                
                # Update the file if changed
                with open(parser_file, 'w', encoding='utf-8') as f:
                    f.write(content)
        
        logger.info("[OK] Fixed integration issues")
        return True
    except Exception as e:
        logger.error(f"Error fixing integration: {e}")
        logger.error(traceback.format_exc())
        return False

def initialize_database():
    """Create initial database objects if needed"""
    try:
        try:
            # Import models
            from admin_panel.models import BotSettings, TelegramSession, Category, Channel
            
            # Create default BotSettings if none exist
            if not BotSettings.objects.exists():
                BotSettings.objects.create(
                    bot_token=os.environ.get('BOT_TOKEN', '8102516142:AAFTsVXXujHHKoX2KZGqZXBHPBznfgh7kg0'),
                    bot_username=os.environ.get('BOT_USERNAME', 'chan_parsing_mon_bot'),
                    bot_name='Telegram Channel Parser',
                    menu_style='buttons'
                )
                logger.info("Created default BotSettings")
            else:
                # Update existing BotSettings with current token
                settings = BotSettings.objects.first()
                settings.bot_token = os.environ.get('BOT_TOKEN', '8102516142:AAFTsVXXujHHKoX2KZGqZXBHPBznfgh7kg0')
                settings.bot_username = os.environ.get('BOT_USERNAME', 'chan_parsing_mon_bot')
                settings.save()
                logger.info("Updated existing BotSettings")
            
            # Create default Category if none exist
            if not Category.objects.exists():
                Category.objects.create(
                    name='Default',
                    description='Default category for channels'
                )
                logger.info("Created default Category")
            
            logger.info("[OK] Database initialized with default objects")
            return True
        except Exception as e:
            logger.error(f"Error initializing database: {e}")
            logger.error(traceback.format_exc())
            return False
    except Exception as e:
        logger.error(f"Unexpected error in initialize_database: {e}")
        logger.error(traceback.format_exc())
        return False

def restart_services():
    """Restart all services"""
    try:
        services = {
            'run.py': 'Run all services',
            'direct_bot_runner.py': 'Telegram bot',
            'run_bot.py': 'Telegram bot',
            'run_parser.py': 'Parser',
            'manage.py': 'Django server'
        }
        
        # Check which services are available
        available_services = {}
        for script, name in services.items():
            script_path = Path(script)
            if script_path.exists():
                available_services[script_path] = name
        
        if not available_services:
            logger.error("No service scripts found")
            return False
        
        # Kill any existing processes
        kill_existing_processes()
        
        # Restart services
        if Path('run.py') in available_services:
            # Use run.py to start all services
            logger.info("Starting all services using run.py")
            
            flags = 0
            if sys.platform == "win32":
                flags = subprocess.CREATE_NEW_PROCESS_GROUP | subprocess.DETACHED_PROCESS
            
            subprocess.Popen(
                [sys.executable, 'run.py'],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                creationflags=flags if sys.platform == "win32" else 0,
                start_new_session=True if sys.platform != "win32" else False
            )
        else:
            # Start individual services
            for script_path, name in available_services.items():
                logger.info(f"Starting {name} using {script_path}")
                
                flags = 0
                if sys.platform == "win32":
                    flags = subprocess.CREATE_NEW_PROCESS_GROUP | subprocess.DETACHED_PROCESS
                
                if script_path.name == 'manage.py':
                    # Django server
                    subprocess.Popen(
                        [sys.executable, script_path, 'runserver', '0.0.0.0:8080'],
                        stdout=subprocess.DEVNULL,
                        stderr=subprocess.DEVNULL,
                        creationflags=flags if sys.platform == "win32" else 0,
                        start_new_session=True if sys.platform != "win32" else False
                    )
                else:
                    # Other service
                    subprocess.Popen(
                        [sys.executable, script_path],
                        stdout=subprocess.DEVNULL,
                        stderr=subprocess.DEVNULL,
                        creationflags=flags if sys.platform == "win32" else 0,
                        start_new_session=True if sys.platform != "win32" else False
                    )
        
        logger.info("[OK] All services restarted")
        return True
    except Exception as e:
        logger.error(f"Error restarting services: {e}")
        logger.error(traceback.format_exc())
        return False

def main():
    """Main function to fix all issues"""
    logger.info("=== Starting fix all issues ===")
    
    # Kill existing processes
    kill_existing_processes()
    
    # Fix database issues
    logger.info("Fixing database issues...")
    fix_database_issues()
    
    # Fix templates
    logger.info("Fixing templates...")
    fix_templates()
    
    # Fix views
    logger.info("Fixing views...")
    fix_views()
    
    # Fix integration
    logger.info("Fixing integration issues...")
    fix_integration()
    
    # Initialize database
    logger.info("Initializing database...")
    initialize_database()
    
    # Restart services
    logger.info("Restarting services...")
    restart_services()
    
    logger.info("=== Fix all issues completed ===")
    logger.info("All services have been restarted. Please check if everything is working correctly.")
    
    return True

if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        logger.error(traceback.format_exc())
    sys.exit(0) 