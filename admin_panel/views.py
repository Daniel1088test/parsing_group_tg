from django.shortcuts import render, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib.auth import login, authenticate, logout
from django.shortcuts import redirect
from django.contrib import messages
from django.contrib.auth.forms import AuthenticationForm
from .models import Category, Message, Channel, TelegramSession
from .forms import ChannelForm, CategoryForm, MessageForm, UserRegistrationForm
from django.core.paginator import Paginator
from django.conf import settings
from .forms import TelegramSessionForm
from .models import BotSettings

def index_view(request):
    # Get filtering parameters from the request
    category_id = request.GET.get('category')
    session_filter = request.GET.get('session')
    count = int(request.GET.get('count', 5))  # Default to 5 messages
    
    # Get messages with filtering
    messages_query = Message.objects.all().order_by('-created_at').select_related('channel', 'channel__category')
    
    # Apply filters if provided
    if category_id and category_id != 'None' and category_id != 'undefined':
        messages_query = messages_query.filter(channel__category_id=category_id)
    
    if session_filter and session_filter != 'None' and session_filter != 'undefined':
        messages_query = messages_query.filter(channel__session_id=session_filter)
    
    # Limit the number of messages
    messages = messages_query[:count]
    
    # Get categories for the filter
    categories = Category.objects.all().order_by('name')
    
    # Get sessions for filter dropdown (handle missing fields safely)
    try:
        sessions = TelegramSession.objects.all().order_by('phone').only('id', 'phone', 'is_active')
    except Exception as e:
        # If there's any issue with the TelegramSession model fields, return empty list
        sessions = []
        
    # Build context for template
    context = {
        'messages': messages,
        'categories': categories,
        'sessions': sessions,
        'selected_category': category_id if category_id and category_id != 'None' and category_id != 'undefined' else '',
        'selected_session': session_filter if session_filter and session_filter != 'None' and session_filter != 'undefined' else '',
        'current_count': count,
    }
    
    return render(request, 'admin_panel/index.html', context)


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
    """View for listing all messages"""
    if not request.user.is_authenticated:
        return redirect('login')
    
    # Get messages with pagination
    messages = Message.objects.all().select_related('channel').order_by('-created_at')
    
    # Apply filters if provided
    channel_id = request.GET.get('channel')
    category_id = request.GET.get('category')
    
    if channel_id:
        messages = messages.filter(channel_id=channel_id)
    
    if category_id:
        messages = messages.filter(channel__category_id=category_id)
    
    # Get channels and categories for filter dropdowns
    channels = Channel.objects.all()
    categories = Category.objects.all()
    
    # Pagination
    paginator = Paginator(messages, 20)  # Show 20 messages per page
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    context = {
        'page_obj': page_obj,
        'channels': channels,
        'categories': categories,
        'active_tab': 'messages',
        'selected_channel': channel_id,
        'selected_category': category_id,
    }
    
    return render(request, 'admin_panel/messages_list.html', context)

@login_required
def message_detail_view(request, message_id):
    """View for viewing message details"""
    if not request.user.is_authenticated:
        return redirect('login')
    
    message = get_object_or_404(Message, id=message_id)
    
    context = {
        'message': message,
        'active_tab': 'messages',
    }
    
    return render(request, 'admin_panel/message_detail.html', context)

@login_required
def message_delete_view(request, message_id):
    """View for deleting a message"""
    if not request.user.is_authenticated:
        return redirect('login')
    
    message = get_object_or_404(Message, id=message_id)
    
    if request.method == 'POST':
        message.delete()
        messages.success(request, 'Message deleted successfully.')
        return redirect('messages_list')
    
    context = {
        'message': message,
        'active_tab': 'messages',
    }
    
    return render(request, 'admin_panel/message_delete.html', context)

# Add the missing session management views
@login_required
def sessions_list_view(request):
    """View for listing all Telegram sessions"""
    if not request.user.is_authenticated:
        return redirect('login')
    
    # Get all sessions
    sessions = TelegramSession.objects.all().order_by('phone')
    
    context = {
        'sessions': sessions,
        'active_tab': 'sessions',
    }
    
    return render(request, 'admin_panel/sessions_list.html', context)

@login_required
def session_create_view(request):
    """View for creating a new Telegram session"""
    if not request.user.is_authenticated:
        return redirect('login')
    
    if request.method == 'POST':
        form = TelegramSessionForm(request.POST)
        if form.is_valid():
            session = form.save(commit=False)
            
            # Set default values if needed
            if not session.api_id:
                session.api_id = settings.DEFAULT_API_ID
            if not session.api_hash:
                session.api_hash = settings.DEFAULT_API_HASH
                
            session.save()
            messages.success(request, f'Telegram session for {session.phone} created successfully.')
            return redirect('sessions_list')
    else:
        form = TelegramSessionForm()
    
    context = {
        'form': form,
        'active_tab': 'sessions',
    }
    
    return render(request, 'admin_panel/session_form.html', context)

@login_required
def session_update_view(request, session_id):
    """View for updating a Telegram session"""
    if not request.user.is_authenticated:
        return redirect('login')
    
    session = get_object_or_404(TelegramSession, id=session_id)
    
    if request.method == 'POST':
        form = TelegramSessionForm(request.POST, instance=session)
        if form.is_valid():
            form.save()
            messages.success(request, f'Telegram session for {session.phone} updated successfully.')
            return redirect('sessions_list')
    else:
        form = TelegramSessionForm(instance=session)
    
    context = {
        'form': form,
        'session': session,
        'active_tab': 'sessions',
    }
    
    return render(request, 'admin_panel/session_form.html', context)

@login_required
def session_delete_view(request, session_id):
    """View for deleting a Telegram session"""
    if not request.user.is_authenticated:
        return redirect('login')
    
    session = get_object_or_404(TelegramSession, id=session_id)
    
    if request.method == 'POST':
        session.delete()
        messages.success(request, f'Telegram session for {session.phone} deleted successfully.')
        return redirect('sessions_list')
    
    context = {
        'session': session,
        'active_tab': 'sessions',
    }
    
    return render(request, 'admin_panel/session_delete.html', context)

@login_required
def authorize_session_view(request, session_id):
    """View for authorizing a Telegram session"""
    if not request.user.is_authenticated:
        return redirect('login')
    
    session = get_object_or_404(TelegramSession, id=session_id)
    
    # Check if the database has been updated with the new fields
    has_verification_field = hasattr(session, 'verification_code')
    has_password_field = hasattr(session, 'password')
    
    # Handling session authorization
    if request.method == 'POST':
        if 'code' in request.POST and has_verification_field:
            # Handle verification code input
            code = request.POST.get('code')
            try:
                session.verification_code = code
                session.save(update_fields=['verification_code'])
                messages.success(request, 'Verification code saved. The system will attempt to authenticate.')
            except Exception as e:
                messages.error(request, f'Error saving verification code: {str(e)}')
            return redirect('sessions_list')
        elif 'password' in request.POST and has_password_field:
            # Handle 2FA password input
            password = request.POST.get('password')
            try:
                session.password = password
                session.save(update_fields=['password'])
                messages.success(request, 'Two-factor password saved. The system will attempt to authenticate.')
            except Exception as e:
                messages.error(request, f'Error saving password: {str(e)}')
            return redirect('sessions_list')
        else:
            # Fallback if fields are missing
            messages.warning(request, 'Database schema update required. Please run migrations first.')
            return redirect('sessions_list')
    
    # Check if we need to show a database update warning
    show_warning = not (has_verification_field and has_password_field)
    
    context = {
        'session': session,
        'active_tab': 'sessions',
        'show_db_warning': show_warning,
        'has_verification_field': has_verification_field,
        'has_password_field': has_password_field,
    }
    
    return render(request, 'admin_panel/authorize_session.html', context)

@login_required
def auth_help_view(request):
    """View for displaying authentication help information"""
    if not request.user.is_authenticated:
        return redirect('login')
    
    context = {
        'active_tab': 'sessions',
    }
    
    return render(request, 'admin_panel/auth_help.html', context)

@login_required
def bot_settings_view(request):
    """View for configuring bot settings"""
    if not request.user.is_authenticated:
        return redirect('login')
    
    # Get or create bot settings
    settings_obj, created = BotSettings.objects.get_or_create(pk=1)
    
    if request.method == 'POST':
        form = BotSettingsForm(request.POST, instance=settings_obj)
        if form.is_valid():
            form.save()
            messages.success(request, 'Bot settings updated successfully.')
            return redirect('bot_settings')
    else:
        form = BotSettingsForm(instance=settings_obj)
    
    context = {
        'form': form,
        'active_tab': 'settings',
    }
    
    return render(request, 'admin_panel/bot_settings.html', context)

@login_required
def user_guide_view(request):
    """View for displaying the user guide"""
    if not request.user.is_authenticated:
        return redirect('login')
    
    context = {
        'active_tab': 'guide',
    }
    
    return render(request, 'admin_panel/user_guide.html', context)

@login_required
def run_migrations_view(request):
    """View for running database migrations from the web UI"""
    if not request.user.is_authenticated or not request.user.is_superuser:
        messages.error(request, 'Only superusers can run migrations')
        return redirect('admin_panel')
    
    if request.method == 'POST':
        try:
            # Import the migrations script and run it
            from scripts.run_migrations import run_migrations
            
            success = run_migrations()
            
            if success:
                messages.success(request, 'Migrations applied successfully')
            else:
                messages.error(request, 'Error applying migrations')
        except Exception as e:
            messages.error(request, f'Error: {str(e)}')
    
    context = {
        'active_tab': 'settings',
    }
    
    return render(request, 'admin_panel/run_migrations.html', context)
