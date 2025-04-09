from django.shortcuts import render, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib.auth import login, authenticate, logout
from django.shortcuts import redirect
from django.contrib import messages
from django.contrib.auth.forms import AuthenticationForm
from .models import Category, Message, Channel, TelegramSession, BotSettings
from .forms import ChannelForm, CategoryForm, MessageForm, UserRegistrationForm
from django.http import HttpResponse
import logging
import traceback
import os
from django.conf import settings
import time
from urllib.parse import quote_plus
from django.db import connection, ProgrammingError, OperationalError
from django.core.exceptions import FieldError
from django.db.utils import DatabaseError

logger = logging.getLogger(__name__)

def safe_db_query(func):
    """Decorator to safely handle database field errors"""
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except (ProgrammingError, OperationalError, FieldError) as e:
            from django.contrib import messages
            from django.shortcuts import redirect
            
            # Log the error
            import logging
            logger = logging.getLogger('django')
            logger.error(f"Database error in {func.__name__}: {e}")
            
            # Get the request object
            request = args[0] if args else None
            
            if request:
                messages.error(request, f"Database error: The system cannot complete this operation. Please contact the administrator. Error: {e}")
                return redirect('home')  # Redirect to a safe page
            
            # If we couldn't get request, raise a more generic HttpResponse
            from django.http import HttpResponse
            return HttpResponse("Database error. Please contact the administrator.", status=500)
    
    return wrapper

def index_view(request):
    """Головна сторінка сайту"""
    try:
        # Логуємо початок виконання
        logger.info("Початок виконання index_view")
        
        # Отримуємо параметри фільтрації
        category_id = request.GET.get('category')
        count = int(request.GET.get('count', 5))
        session_filter = request.GET.get('session')
        
        # Завантажуємо категорії
        try:
            categories = Category.objects.all()
            logger.info(f"Завантажено {len(categories)} категорій")
        except Exception as e:
            categories = []
            logger.error(f"Помилка завантаження категорій: {str(e)}")
        
        # Завантажуємо повідомлення
        try:
            # Use a safer approach with raw SQL to avoid field errors
            messages_query = []
            try:
                messages_query = Message.objects.select_related('channel', 'session_used', 'channel__session').order_by('-created_at')
                
                # Фільтруємо за категорією, якщо вона вказана
                if category_id and category_id != 'None' and category_id != 'undefined':
                    try:
                        category_id = int(category_id)
                        messages_query = messages_query.filter(channel__category_id=category_id)
                    except (ValueError, TypeError):
                        pass
                
                # Фільтруємо за сесією, якщо вона вказана
                if session_filter and session_filter != 'None' and session_filter != 'undefined':
                    try:
                        session_id = int(session_filter)
                        messages_query = messages_query.filter(session_used_id=session_id)
                    except (ValueError, TypeError):
                        pass
                
                # Обмежуємо кількість повідомлень
                messages_list = messages_query[:count]
            except Exception as e:
                # If there's a field error, fall back to raw SQL
                logger.error(f"Error with ORM query: {e}. Falling back to raw SQL.")
                
                # Simple queries without the problematic fields
                with connection.cursor() as cursor:
                    cursor.execute("""
                        SELECT m.id, m.text, m.media, m.telegram_message_id, m.created_at
                        FROM admin_panel_message m
                        ORDER BY m.created_at DESC
                        LIMIT %s
                    """, [count])
                    
                    columns = ['id', 'text', 'media', 'telegram_message_id', 'created_at']
                    messages_list = [dict(zip(columns, row)) for row in cursor.fetchall()]
                    
            logger.info(f"Завантажено {len(messages_list)} повідомлень")
        except Exception as e:
            messages_list = []
            logger.error(f"Помилка завантаження повідомлень: {str(e)}")
        
        # Завантажуємо активні сесії
        try:
            # First attempt using the ORM
            try:
                sessions = TelegramSession.objects.filter(is_active=True).order_by('phone')
            except Exception as field_e:
                # If there's a field error, fall back to raw SQL
                logger.error(f"Error loading sessions with ORM: {field_e}. Falling back to raw SQL.")
                with connection.cursor() as cursor:
                    cursor.execute("""
                        SELECT id, phone, is_active
                        FROM admin_panel_telegramsession
                        WHERE is_active = TRUE
                        ORDER BY phone
                    """)
                    columns = ['id', 'phone', 'is_active']
                    sessions = [dict(zip(columns, row)) for row in cursor.fetchall()]
                    
            logger.info(f"Завантажено {len(sessions)} сесій")
        except Exception as e:
            sessions = []
            logger.error(f"Помилка завантаження сесій: {str(e)}")
        
        # Формуємо контекст для шаблону
        context = {
            'categories': categories,
            'messages': messages_list,
            'sessions': sessions,
            'selected_category': category_id if category_id and category_id != 'None' and category_id != 'undefined' else '',
            'selected_session': session_filter if session_filter and session_filter != 'None' and session_filter != 'undefined' else '',
            'current_count': count,
            'MEDIA_URL': settings.MEDIA_URL,
        }
        
        # Перевіряємо, чи існує шаблон
        template_path = os.path.join(settings.BASE_DIR, 'templates', 'admin_panel', 'index.html')
        if os.path.exists(template_path):
            logger.info(f"Шаблон знайдено: {template_path}")
        else:
            logger.error(f"Шаблон не знайдено: {template_path}")
            # Спробуємо знайти будь-який шаблон в папці admin_panel
            template_dir = os.path.join(settings.BASE_DIR, 'templates', 'admin_panel')
            if os.path.exists(template_dir):
                templates = [f for f in os.listdir(template_dir) if f.endswith('.html')]
                logger.info(f"Доступні шаблони: {templates}")
        
        # Рендеримо шаблон
        logger.info("Рендеримо шаблон index.html")
        return render(request, 'admin_panel/index.html', context)
        
    except Exception as e:
        logger.error(f"Критична помилка в index_view: {str(e)}\n{traceback.format_exc()}")
        
        # Повертаємо просту HTML-сторінку
        return HttpResponse(f"""
        <!DOCTYPE html>
        <html lang="uk">
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>Telegram Parser</title>
            <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.2/dist/css/bootstrap.min.css" rel="stylesheet">
            <style>
                body {{ padding: 20px; }}
                .error {{ color: red; background: #ffeeee; padding: 10px; border-radius: 5px; margin: 20px 0; }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="row">
                    <div class="col-md-8 offset-md-2">
                        <h1 class="text-primary mt-5">Telegram Channel Parser</h1>
                        <p class="lead">Додаток працює, але виникла помилка при завантаженні повної сторінки.</p>
                        
                        <div class="error">
                            <h4>Деталі помилки:</h4>
                            <p>{str(e)}</p>
                        </div>
                        
                        <div class="d-grid gap-3 col-md-6 mx-auto mt-4">
                            <a href="/admin/" class="btn btn-primary">Адмін-панель Django</a>
                            <a href="https://t.me/Channels_hunt_bot" class="btn btn-info">Відкрити Telegram бот</a>
                        </div>
                    </div>
                </div>
            </div>
            
            <script src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.2/dist/js/bootstrap.bundle.min.js"></script>
        </body>
        </html>
        """)


def login_view(request):
    """View for user login"""
    if request.user.is_authenticated:
        return redirect('admin_panel')
    if request.method == 'POST':
        form = AuthenticationForm(request, data=request.POST)
        if form.is_valid():
            user = authenticate(
                username=form.cleaned_data['username'],
                password=form.cleaned_data['password']
            )
            if user is not None:
                login(request, user)
                return redirect('admin_panel')
    else:
        form = AuthenticationForm()
    return render(request, 'admin_panel/login.html', {'form': form})

def register_view(request):
    """View for user registration"""
    if request.user.is_authenticated:
        return redirect('admin_panel')
        
    if request.method == 'POST':
        form = UserRegistrationForm(request.POST)
        if form.is_valid():
            try:
                # Збереження користувача
                user = form.save()
                # Повідомлення про успішну реєстрацію
                messages.success(request, 'Реєстрація успішна! Тепер ви можете увійти.')
                # Перенаправлення на сторінку входу
                return redirect('login')
            except Exception as e:
                # Обробка помилок під час збереження
                messages.error(request, f'Помилка при створенні користувача: {str(e)}')
        else:
            # Вивід всіх помилок форми
            for field, errors in form.errors.items():
                for error in errors:
                    messages.error(request, f'{error}')
    else:
        form = UserRegistrationForm()
        
    return render(request, 'admin_panel/register.html', {'form': form})

def logout_view(request):
    logout(request)
    return redirect('index')

@login_required
def admin_panel_view(request):
    channels_count = Channel.objects.count()
    categories_count = Category.objects.count()
    active_channels_count = Channel.objects.filter(is_active=True).count()
    messages_count = Message.objects.count()
    sessions_count = TelegramSession.objects.count()
    latest_messages = Message.objects.order_by('-created_at')
    return render(
        request, 
        'admin_panel/admin_panel.html', 
        {'channels_count': channels_count, 
         'categories_count': categories_count, 
         'active_channels_count': active_channels_count, 
         'messages_count': messages_count,
         'sessions_count': sessions_count,
         'latest_messages': latest_messages})

@login_required
def channels_list_view(request):
    channels = Channel.objects.all()
    return render(request, 'admin_panel/channels_list.html', {'channels': channels})

@login_required
def channel_create_view(request):
    categories = Category.objects.all()
    sessions = TelegramSession.objects.filter(is_active=True).order_by('phone')
    
    if request.method == 'POST':
        form = ChannelForm(request.POST)
        if form.is_valid():
            channel = form.save()
            messages.success(request, 'Channel successfully created.')
            return redirect('channels_list')
    else:
        form = ChannelForm()
    
    return render(request, 'admin_panel/channel_form.html', {
        'form': form,
        'categories': categories,
        'sessions': sessions,
        'title': 'Create channel'
    })

@login_required
@safe_db_query
def channel_detail_view(request, channel_id):
    channel = Channel.objects.get(id=channel_id)
    messages = Message.objects.filter(channel=channel).order_by('-created_at')[:100]
    
    context = {
        'channel': channel,
        'messages': messages,
        'title': f'Канал {channel.name}'
    }
    return render(request, 'admin_panel/channel_detail.html', context)

@login_required
def channel_update_view(request, channel_id):
    channel = get_object_or_404(Channel, pk=channel_id)
    categories = Category.objects.all()
    sessions = TelegramSession.objects.filter(is_active=True).order_by('phone')
    
    if request.method == 'POST':
        form = ChannelForm(request.POST, instance=channel)
        if form.is_valid():
            channel = form.save()
            messages.success(request, 'Channel successfully updated.')
            return redirect('channels_list')
    else:
        form = ChannelForm(instance=channel)
    
    return render(request, 'admin_panel/channel_form.html', {
        'form': form,
        'channel': channel,
        'categories': categories,
        'sessions': sessions,
        'title': 'Update channel'
    })

@login_required
def channel_delete_view(request, channel_id):
    channel = Channel.objects.get(id=channel_id)
    channel.delete()
    return redirect('channels_list')

@login_required
def categories_list_view(request):
    categories = Category.objects.all()
    return render(request, 'admin_panel/categories_list.html', {'categories': categories})

@login_required
def category_create_view(request):
    sessions = TelegramSession.objects.filter(is_active=True).order_by('phone')
    
    if request.method == 'POST':
        form = CategoryForm(request.POST)
        if form.is_valid():
            category = form.save()
            messages.success(request, 'Category successfully created.')
            return redirect('categories_list')
    else:
        form = CategoryForm()   
    return render(request, 'admin_panel/category_form.html', {
        'form': form,
        'sessions': sessions,
        'title': 'Create category'
    })

@login_required
def category_detail_view(request, category_id):
    category = get_object_or_404(Category, pk=category_id)
    return render(request, 'admin_panel/category_detail.html', {'category': category})

@login_required
def category_update_view(request, category_id):
    category = get_object_or_404(Category, pk=category_id)
    sessions = TelegramSession.objects.filter(is_active=True).order_by('phone')
    
    if request.method == 'POST':
        form = CategoryForm(request.POST, instance=category)
        if form.is_valid():
            category = form.save()
            messages.success(request, 'Category successfully updated.')
            return redirect('categories_list')
    else:
        form = CategoryForm(instance=category)  
    return render(request, 'admin_panel/category_form.html', {
        'form': form,
        'category': category,
        'sessions': sessions,
        'title': 'Update category'
    })

@login_required
def category_delete_view(request, category_id):
    category = get_object_or_404(Category, pk=category_id)
    category.delete()
    return redirect('categories_list')

@login_required
def messages_list_view(request):
    messages = Message.objects.all()
    return render(request, 'admin_panel/messages_list.html', {'messages': messages})

@login_required
def message_detail_view(request, message_id):
    message = get_object_or_404(Message, pk=message_id)
    return render(request, 'admin_panel/message_detail.html', {'message': message}) 

@login_required
def message_delete_view(request, message_id):
    message = get_object_or_404(Message, pk=message_id)
    message.delete()
    return redirect('messages_list')

@login_required
def sessions_list_view(request):
    """View for listing all Telegram sessions"""
    
    # Process any session fixer actions
    if request.method == 'POST' and 'action' in request.POST:
        action = request.POST.get('action')
        session_id = request.POST.get('session_id')
        
        if action == 'fix_session' and session_id:
            try:
                session = TelegramSession.objects.get(id=session_id)
                
                # Check for a session file and ensure we mark it as authenticated if found
                try:
                    session_name = session.session_file or f"telethon_session_{session.phone.replace('+', '')}"
                except AttributeError:
                    # Handle case where session_file doesn't exist
                    session_name = f"telethon_session_{session.phone.replace('+', '')}"
                
                session_paths = [
                    f"{session_name}.session",
                    f"data/sessions/{session_name}.session"
                ]
                
                file_found = False
                for path in session_paths:
                    if os.path.exists(path):
                        file_found = True
                        break
                
                if file_found:
                    try:
                        if hasattr(session, 'needs_auth'):
                            session.needs_auth = False
                            session.save(update_fields=['needs_auth'])
                            messages.success(request, f'Session {session.phone} marked as authenticated')
                    except (AttributeError, DatabaseError):
                        messages.warning(request, f'Cannot update needs_auth for session {session.phone} (database schema may need updating)')
                else:
                    messages.warning(request, f'No session file found for {session.phone}. Please authenticate this session.')
            except TelegramSession.DoesNotExist:
                messages.error(request, f'Session with ID {session_id} not found')
            except Exception as e:
                messages.error(request, f'Error fixing session: {str(e)}')
                request.session['error_message'] = str(e)
            
        elif action == 'fix_auth_status':
            try:
                # Run management command to fix sessions
                from django.core.management import call_command
                call_command('fix_sessions', sessions_only=True)
                messages.success(request, f'Session authentication status fixed for all sessions.')
            except Exception as e:
                messages.error(request, f'Error fixing session authentication status: {str(e)}')
                request.session['error_message'] = str(e)
            
        elif action == 'fix_media':
            try:
                # Run management command to fix media
                from django.core.management import call_command
                call_command('fix_sessions', media_only=True)
                messages.success(request, f'Media files fixed. Check the console for details.')
            except Exception as e:
                messages.error(request, f'Error fixing media files: {str(e)}')
                request.session['error_message'] = str(e)
                
        elif action == 'fix_schema':
            # Run our migration to fix schema
            try:
                from django.core.management import call_command
                call_command('migrate', 'admin_panel')
                messages.success(request, 'Database schema fixed. Refresh the page to see the changes.')
            except Exception as e:
                messages.error(request, f'Error fixing database schema: {str(e)}')
                request.session['error_message'] = str(e)
                
        # Handle session creation (directly from the list page)
        elif action == '' or action is None:
            # If no action specified, treat as session creation
            phone = request.POST.get('phone')
            api_id = request.POST.get('api_id', '')
            api_hash = request.POST.get('api_hash', '')
            
            if not phone:
                messages.error(request, 'Phone number is required')
                return redirect('sessions_list')
            
            # Create the session
            try:
                session_data = {
                    'phone': phone,
                    'api_id': api_id or settings.TELEGRAM_API_ID,
                    'api_hash': api_hash or settings.TELEGRAM_API_HASH,
                    'is_active': True,
                }
                
                # needs_auth field is temporarily removed 
                session = TelegramSession(**session_data)
                session.save()
                
                messages.success(request, f'Session created for {phone}.')
                messages.info(request, f'Please authenticate it using the Authorize button.')
                
            except Exception as e:
                messages.error(request, f'Error creating session: {str(e)}')
                request.session['error_message'] = str(e)
                
        # Handle session update
        elif action == 'update_session' and session_id:
            try:
                session = TelegramSession.objects.get(id=session_id)
                
                # Update basic properties
                session.phone = request.POST.get('phone', session.phone)
                session.api_id = request.POST.get('api_id', session.api_id)
                session.api_hash = request.POST.get('api_hash', session.api_hash)
                session.is_active = request.POST.get('is_active') == 'on'
                
                # Save the session
                session.save()
                
                messages.success(request, f'Session {session.phone} updated')
            except TelegramSession.DoesNotExist:
                messages.error(request, f'Session with ID {session_id} not found')
            except Exception as e:
                messages.error(request, f'Error updating session: {str(e)}')
                
        # Handle session deletion
        elif action == 'delete_session' and session_id:
            try:
                session = TelegramSession.objects.get(id=session_id)
                
                # Check if this session is in use
                if Channel.objects.filter(session=session).exists():
                    messages.error(request, f'Cannot delete session {session.phone} as it is used by channels')
                else:
                    # Delete the session
                    session.delete()
                    messages.success(request, f'Session {session.phone} deleted')
            except TelegramSession.DoesNotExist:
                messages.error(request, f'Session with ID {session_id} not found')
            except Exception as e:
                messages.error(request, f'Error deleting session: {str(e)}')
    
    # Get all sessions
    try:
        sessions = TelegramSession.objects.all().order_by('-is_active', 'id')
        
        # Add needs_auth attribute if it doesn't exist in the database
        for session in sessions:
            if not hasattr(session, 'needs_auth'):
                session.needs_auth = True
        
        # Check if we need to update session status (has valid data but marked as needs_auth)
        for session in sessions:
            try:
                if hasattr(session, 'needs_auth') and session.needs_auth and hasattr(session, 'session_data') and session.session_data:
                    # If we have session data, but it's marked as needing auth, update it
                    session.needs_auth = False
                    session.save(update_fields=['needs_auth'])
            except (AttributeError, DatabaseError):
                # Skip if database fields are missing
                pass
                
        # Count channels per session
        for session in sessions:
            session.channels_count = session.channels.count() if hasattr(session, 'channels') else 0
            session.messages_count = session.messages.count() if hasattr(session, 'messages') else 0
    
    except Exception as e:
        logger.error(f"Error loading sessions: {e}")
        request.session['error_message'] = str(e)
        
        # Use raw queries as fallback
        with connection.cursor() as cursor:
            try:
                cursor.execute("""
                    SELECT id, phone, is_active, 
                    created_at, updated_at
                    FROM admin_panel_telegramsession
                    ORDER BY id DESC
                """)
                columns = [col[0] for col in cursor.description]
                sessions = [
                    dict(zip(columns, row))
                    for row in cursor.fetchall()
                ]
                # Add missing attributes to dictionaries
                for session in sessions:
                    # Use dictionary-style access since these are dicts, not objects
                    session['needs_auth'] = True
                    session['channels_count'] = 0
                    session['messages_count'] = 0
                    session['session_file'] = ''
            except Exception as inner_e:
                logger.error(f"Error with fallback query: {inner_e}")
                sessions = []
    
    context = {
        'sessions': sessions,
        'schema_error': 'session_name' in request.session.get('error_message', '')
    }
    return render(request, 'admin_panel/sessions_list.html', context)

@login_required
def session_create_view(request):
    """View for creating a new Telegram session"""
    if request.method == 'POST':
        phone = request.POST.get('phone')
        api_id = request.POST.get('api_id', '')
        api_hash = request.POST.get('api_hash', '')
        
        if not phone:
            messages.error(request, 'Phone number is required')
            return redirect('sessions_list')
        
        # Create the session
        try:
            session_data = {
                'phone': phone,
                'api_id': api_id or settings.TELEGRAM_API_ID,
                'api_hash': api_hash or settings.TELEGRAM_API_HASH,
                'is_active': True,
            }
            
            # needs_auth field is temporarily removed 
            session = TelegramSession(**session_data)
            session.save()
            
            messages.success(request, f'Session created for {phone}. Please authenticate it using the command:')
            messages.info(request, f'python manage.py authsession --auth {session.id}')
            
        except Exception as e:
            messages.error(request, f'Error creating session: {str(e)}')
            
    return redirect('sessions_list')

@login_required
def session_update_view(request, session_id):
    """View for updating a Telegram session"""
    session = get_object_or_404(TelegramSession, pk=session_id)
    
    if request.method == 'POST':
        # Update basic properties
        session.phone = request.POST.get('phone', session.phone)
        session.api_id = request.POST.get('api_id', session.api_id)
        session.api_hash = request.POST.get('api_hash', session.api_hash)
        session.is_active = request.POST.get('is_active') == 'on'
        
        # Save the session
        session.save()
        
        messages.success(request, f'Session {session.phone} updated')
        
    return redirect('sessions_list')

@login_required
def session_delete_view(request, session_id):
    """View for deleting a Telegram session"""
    session = get_object_or_404(TelegramSession, pk=session_id)
    
    # Check if this session is in use
    if Channel.objects.filter(session=session).exists():
        messages.error(request, f'Cannot delete session {session.phone} as it is used by channels')
        return redirect('sessions_list')
        
    if Message.objects.filter(session_used=session).exists():
        messages.warning(request, f'Deleting session {session.phone} which has associated messages')
    
    # Delete the session
    session.delete()
    messages.success(request, f'Session {session.phone} deleted')
    
    return redirect('sessions_list')

@login_required
def auth_help_view(request):
    """View for the Telegram authentication help page"""
    return render(request, 'admin_panel/auth_help.html')

@login_required
def bot_settings_view(request):
    """View for managing bot settings"""
    # Get or create settings
    settings = BotSettings.get_settings()
    
    if request.method == 'POST':
        # Update settings
        settings.bot_username = request.POST.get('bot_username', settings.bot_username)
        settings.bot_name = request.POST.get('bot_name', settings.bot_name)
        settings.auth_guide_text = request.POST.get('auth_guide_text', settings.auth_guide_text)
        settings.welcome_message = request.POST.get('welcome_message', settings.welcome_message)
        settings.menu_style = request.POST.get('menu_style', settings.menu_style)
        settings.save()
        
        messages.success(request, "Bot settings updated successfully")
        
        # Restart the bot process if requested
        if request.POST.get('restart_bot') == 'on':
            try:
                import subprocess
                subprocess.run(["python", "manage.py", "runbot"], start_new_session=True)
                messages.success(request, "Bot process restarted")
            except Exception as e:
                messages.error(request, f"Failed to restart bot: {str(e)}")
    
    return render(request, 'admin_panel/bot_settings.html', {
        'settings': settings,
        'title': 'Bot Settings'
    })

@login_required
def user_guide_view(request):
    """View for the user guide page"""
    return render(request, 'admin_panel/user_guide.html', {
        'title': 'User Guide'
    })

@login_required
def authorize_session_view(request, session_id):
    """View for authorizing a Telegram session directly from the website"""
    session = get_object_or_404(TelegramSession, pk=session_id)
    
    if request.method == 'POST':
        try:
            # Generate QR code authorization link
            from urllib.parse import quote_plus
            
            # Generate a unique deep link to the bot
            bot_username = getattr(settings, 'TELEGRAM_BOT_USERNAME', 'Channels_hunt_bot')
            authorization_token = f"auth_{session_id}_{int(time.time())}"
            deep_link = f"https://t.me/{bot_username}?start={authorization_token}"
            
            # Store the authorization token in the session
            if not hasattr(session, 'auth_token') or not session.auth_token:
                session.auth_token = authorization_token
                session.save()
            
            # Send success message with link
            messages.success(request, 'Click the button below to authorize this session via Telegram bot')
            
            context = {
                'session': session,
                'deep_link': deep_link,
                'title': f'Authorize Session: {session.phone}'
            }
            return render(request, 'admin_panel/authorize_session.html', context)
            
        except Exception as e:
            messages.error(request, f'Error starting authorization: {str(e)}')
    
    # If GET request, show confirmation page
    context = {
        'session': session,
        'title': f'Authorize Session: {session.phone}'
    }
    return render(request, 'admin_panel/authorize_session_confirm.html', context)

@login_required
def run_migrations_view(request):
    """View for running database migrations"""
    if request.method == 'POST':
        try:
            # Import and run the migration script
            from scripts.run_migrations import run_migrations
            success = run_migrations()
            
            if success:
                messages.success(request, "Database migrations have been applied successfully.")
            else:
                messages.error(request, "Failed to apply migrations. Please check the logs.")
        except Exception as e:
            messages.error(request, f"Error running migrations: {str(e)}")
    
    return render(request, 'admin_panel/run_migrations.html')

@login_required
@safe_db_query
def channels_view(request):
    """Сторінка зі списком каналів"""
    channels = Channel.objects.all().order_by('-id')
    
    context = {
        'channels': channels,
        'title': 'Канали'
    }
    return render(request, 'admin_panel/channels.html', context)

@login_required
@safe_db_query
def telegram_sessions_view(request):
    """Сторінка зі списком сесій Telegram"""
    try:
        # Try to use Django's ORM first
        sessions = TelegramSession.objects.all().order_by('-id')
    except Exception as e:
        logger.error(f"Error loading TelegramSession: {e}")
        # Use raw query to get only essential fields that should exist
        with connection.cursor() as cursor:
            try:
                cursor.execute("""
                    SELECT id, phone, is_active, 
                    CASE WHEN needs_auth IS NULL THEN 1 ELSE needs_auth END as needs_auth,
                    CASE WHEN session_file IS NULL THEN '' ELSE session_file END as session_file,
                    created_at, updated_at
                    FROM admin_panel_telegramsession
                    ORDER BY id DESC
                """)
                columns = [col[0] for col in cursor.description]
                sessions = [
                    dict(zip(columns, row))
                    for row in cursor.fetchall()
                ]
            except Exception as inner_e:
                # If even the safer query fails, use the most minimal query
                logger.error(f"Error with safer query: {inner_e}")
                cursor.execute("""
                    SELECT id, phone, 
                    CASE WHEN is_active IS NULL THEN 1 ELSE is_active END as is_active,
                    created_at, updated_at
                    FROM admin_panel_telegramsession
                    ORDER BY id DESC
                """)
                columns = [col[0] for col in cursor.description]
                sessions = [
                    dict(zip(columns, row))
                    for row in cursor.fetchall()
                ]
                # Add missing attributes
                for session in sessions:
                    session['needs_auth'] = True
                    session['session_file'] = ''
    
    context = {
        'sessions': sessions,
        'title': 'Сесії Telegram',
        'migration_needed': 'session_name' in request.session.get('error_message', '') or 'is_bot' in request.session.get('error_message', '')
    }
    return render(request, 'admin_panel/telegram_sessions.html', context)

@login_required
@safe_db_query
def add_session_view(request):
    """Сторінка додавання нової сесії Telegram"""
    if request.method == 'POST':
        form = TelegramSession(request.POST)
        if form.is_valid():
            session = form.save()
            messages.success(request, f'Сесія {session.phone} успішно додана!')
            return redirect('telegram_sessions')
    else:
        form = TelegramSession()
    
    context = {
        'form': form,
        'title': 'Додати сесію Telegram'
    }
    return render(request, 'admin_panel/add_session.html', context)

@login_required
@safe_db_query
def edit_session_view(request, session_id):
    """Сторінка редагування сесії Telegram"""
    session = TelegramSession.objects.get(id=session_id)
    
    if request.method == 'POST':
        form = TelegramSession.objects.get(request.POST, instance=session)
        if form.is_valid():
            form.save()
            messages.success(request, f'Сесія {session.phone} успішно оновлена!')
            return redirect('telegram_sessions')
    else:
        form = TelegramSession(instance=session)
    
    context = {
        'form': form,
        'session': session,
        'title': f'Редагування сесії {session.phone}'
    }
    return render(request, 'admin_panel/edit_session.html', context)
