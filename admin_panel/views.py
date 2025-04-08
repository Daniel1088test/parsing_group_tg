from django.shortcuts import render, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib.auth import login, authenticate, logout
from django.shortcuts import redirect
from django.contrib import messages
from django.contrib.auth.forms import AuthenticationForm
from .models import Category, Message, Channel, TelegramSession
from .forms import ChannelForm, CategoryForm, MessageForm, UserRegistrationForm
from django.http import HttpResponse
import logging
import traceback
import os
from django.conf import settings

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
    latest_messages = Message.objects.order_by('-created_at')
    return render(
        request, 
        'admin_panel/admin_panel.html', 
        {'channels_count': channels_count, 
         'categories_count': categories_count, 
         'active_channels_count': active_channels_count, 
         'messages_count': messages_count,
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
