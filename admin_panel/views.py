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

logger = logging.getLogger(__name__)

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
            logger.info(f"Завантажено {len(messages_list)} повідомлень")
        except Exception as e:
            messages_list = []
            logger.error(f"Помилка завантаження повідомлень: {str(e)}")
        
        # Завантажуємо активні сесії
        try:
            sessions = TelegramSession.objects.filter(is_active=True).order_by('phone')
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
            'current_count': count
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
    if request.user.is_authenticated:
        return redirect('admin_panel')
    if request.method == 'POST':
        form = AuthenticationForm(request, data=request.POST)
        if form.is_valid():
            user = authenticate(
                username=form.cleaned_data['username'],
                password=form.cleaned_data['password']
            )
            login(request, user)
            return redirect('admin_panel')
    else:
        form = AuthenticationForm()
    return render(request, 'admin_panel/login.html', {'form': form})

def register_view(request):
    if request.user.is_authenticated:
        return redirect('admin_panel')
    if request.method == 'POST':
        form = UserRegistrationForm(request.POST)
        if form.is_valid():
            user = form.save()
            messages.success(request, 'Registration successful! Now you can login.')
            return redirect('login')
        else:
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
def channel_detail_view(request, channel_id):
    channel = Channel.objects.get(id=channel_id)
    return render(request, 'admin_panel/channel_detail.html', {'channel': channel})

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
                session_name = session.session_file or f"telethon_session_{session.phone.replace('+', '')}"
                session_paths = [
                    f"{session_name}.session",
                    f"data/sessions/{session_name}.session"
                ]
                
                file_found = False
                for path in session_paths:
                    if os.path.exists(path):
                        file_found = True
                        break
                
                if file_found or session.session_data:
                    # We have either a session file or encoded data, mark as authenticated
                    session.needs_auth = False
                    session.save(update_fields=['needs_auth'])
                    messages.success(request, f'Session {session.phone} marked as authenticated')
                    
                    # If we only have session data but no file, restore the file
                    if not file_found and session.session_data:
                        try:
                            import base64
                            session_data = base64.b64decode(session.session_data)
                            os.makedirs('data/sessions', exist_ok=True)
                            for path in session_paths:
                                with open(path, 'wb') as f:
                                    f.write(session_data)
                            messages.success(request, f'Session file restored from database data')
                        except Exception as e:
                            messages.error(request, f'Error restoring session file: {str(e)}')
                else:
                    messages.error(request, f'No session file or data found for {session.phone}')
                
            except TelegramSession.DoesNotExist:
                messages.error(request, f'Session with ID {session_id} not found')
                
        elif action == 'fix_auth_status':
            # Fix auth status for all sessions with session data
            fixed = 0
            for session in TelegramSession.objects.filter(needs_auth=True, session_data__isnull=False).exclude(session_data=''):
                session.needs_auth = False
                session.save(update_fields=['needs_auth'])
                fixed += 1
            
            messages.success(request, f'Fixed auth status for {fixed} sessions')
            
        elif action == 'fix_media':
            try:
                # Run management command to fix media
                from django.core.management import call_command
                call_command('fix_sessions', media_only=True)
                messages.success(request, f'Media files fixed. Check the console for details.')
            except Exception as e:
                messages.error(request, f'Error fixing media files: {str(e)}')
    
    # Get all sessions
    sessions = TelegramSession.objects.all().order_by('-is_active', 'id')
    
    # Check if we need to update session status (has valid data but marked as needs_auth)
    for session in sessions:
        if hasattr(session, 'needs_auth') and session.needs_auth and session.session_data:
            # If we have session data, but it's marked as needing auth, update it
            session.needs_auth = False
            session.save(update_fields=['needs_auth'])
            
    # Count channels per session
    for session in sessions:
        session.channels_count = session.channels.count() if hasattr(session, 'channels') else 0
        session.messages_count = session.messages.count() if hasattr(session, 'messages') else 0
    
    context = {
        'sessions': sessions,
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
            authorization_token = f"auth_{session_id}_{int(time.time())}"
            
            # Store the authorization token in the session
            if not hasattr(session, 'auth_token') or not session.auth_token:
                session.auth_token = authorization_token
                session.save()
            
            # Send success message with link
            messages.success(request, 'Click the button below to authorize this session via Telegram bot')
            
            context = {
                'session': session,
                'authorization_token': authorization_token,
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
