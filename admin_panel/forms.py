from django import forms
from django.db import connection
from .models import Channel, Category, Message, TelegramSession, BotSettings
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User

class ChannelForm(forms.ModelForm):
    class Meta:
        model = Channel
        fields = ['name', 'url', 'category', 'is_active', 'session']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control'}),
            'url': forms.TextInput(attrs={'class': 'form-control'}),
            'category': forms.Select(attrs={'class': 'form-control'}),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'session': forms.Select(attrs={'class': 'form-control'}),
        }
        labels = {
            'name': 'Channel name',
            'url': 'Channel link',
            'category': 'Category',
            'is_active': 'Status',
            'session': 'Telegram Session',
        }
        help_texts = {
            'is_active': 'Check if the channel should be active',
            'session': 'Select the Telegram session for this channel',
        }
        error_messages = {
            'name': {
                'required': "This field is required.",
                'max_length': 'Channel name is too long.'
            },
            'url': {
                'required': "This field is required.",
                'invalid': 'Enter a valid URL.'
            },
            'category': {
                'required': "This field is required.",
            },
        }

class SafeTelegramSessionForm(forms.ModelForm):
    """
    TelegramSession form that adapts to available database fields
    """
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # Determine which fields actually exist in the database table
        with connection.cursor() as cursor:
            cursor.execute("""
                SELECT column_name 
                FROM information_schema.columns 
                WHERE table_name = 'admin_panel_telegramsession';
            """)
            existing_columns = [row[0] for row in cursor.fetchall()]
        
        # Remove fields that don't exist in the database
        for field_name in list(self.fields.keys()):
            # Skip id, created_at, and updated_at as they're managed by Django
            if field_name in ['id', 'created_at', 'updated_at']:
                continue
                
            if field_name not in existing_columns:
                self.fields.pop(field_name, None)
    
    class Meta:
        model = TelegramSession
        fields = [
            'phone', 'api_id', 'api_hash', 'is_active', 
            'session_file', 'verification_code', 'password',
            'session_data', 'auth_token', 'needs_auth'
        ]
        widgets = {
            'phone': forms.TextInput(attrs={'class': 'form-control'}),
            'api_id': forms.TextInput(attrs={'class': 'form-control'}),
            'api_hash': forms.TextInput(attrs={'class': 'form-control'}),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'session_file': forms.TextInput(attrs={'class': 'form-control'}),
            'verification_code': forms.TextInput(attrs={'class': 'form-control'}),
            'password': forms.PasswordInput(attrs={'class': 'form-control'}),
            'session_data': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'auth_token': forms.TextInput(attrs={'class': 'form-control'}),
            'needs_auth': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }

# For backward compatibility
TelegramSessionForm = SafeTelegramSessionForm

class CategoryForm(forms.ModelForm):
    class Meta:
        model = Category
        fields = ['name', 'description', 'is_active', 'session']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'session': forms.Select(attrs={'class': 'form-control'}),
        }   
        labels = {
            'name': 'Category name',
            'description': 'Description',
            'is_active': 'Active',
            'session': 'Telegram Session',
        }
        help_texts = {
            'name': 'Enter the category name',
            'description': 'Enter the category description (optional)',
            'is_active': 'Check if the category should be active',
            'session': 'Select the Telegram session for this category',
        }
        error_messages = {
            'name': {
                'required': "This field is required.",
                'max_length': 'Category name is too long.'
            },
        }

class MessageForm(forms.ModelForm):
    class Meta:
        model = Message
        fields = ['text', 'media', 'media_type', 'original_url', 'channel']
        widgets = {
            'text': forms.Textarea(attrs={'class': 'form-control', 'rows': 4}),
            'media': forms.ClearableFileInput(attrs={'class': 'form-control'}),
            'media_type': forms.Select(attrs={'class': 'form-control'}),
            'original_url': forms.URLInput(attrs={'class': 'form-control'}),
            'channel': forms.Select(attrs={'class': 'form-control'}),
        }
        labels = {
            'text': 'Message text',
            'media': 'Media',   
            'media_type': 'Media Type',
            'original_url': 'Original URL',
            'channel': 'Channel',
        }
        help_texts = {
            'text': 'Enter the message text',
            'media': 'Add media file',
            'media_type': 'Select the media type',
            'original_url': 'Enter the original URL',
            'channel': 'Select the channel',
        }   
        error_messages = {
            'text': {
                'required': "This field is required.",
            },
            'channel': {
                'required': "This field is required.",
            },
        }

class BotSettingsForm(forms.ModelForm):
    class Meta:
        model = BotSettings
        fields = ['bot_token', 'default_api_id', 'default_api_hash', 'polling_interval', 'max_messages_per_channel']
        widgets = {
            'bot_token': forms.TextInput(attrs={'class': 'form-control'}),
            'default_api_id': forms.NumberInput(attrs={'class': 'form-control'}),
            'default_api_hash': forms.TextInput(attrs={'class': 'form-control'}),
            'polling_interval': forms.NumberInput(attrs={'class': 'form-control'}),
            'max_messages_per_channel': forms.NumberInput(attrs={'class': 'form-control'}),
        }
        help_texts = {
            'bot_token': 'Telegram bot token from @BotFather',
            'default_api_id': 'Default Telegram API ID to use for sessions',
            'default_api_hash': 'Default Telegram API Hash to use for sessions',
            'polling_interval': 'How often to check for new messages (in seconds)',
            'max_messages_per_channel': 'Maximum number of messages to fetch per channel',
        }

class UserRegistrationForm(UserCreationForm):
    """Form for registration of new users"""
    email = forms.EmailField(
        required=True,
        help_text='Enter a valid email address'
    )

    class Meta:
        model = User
        fields = ('username', 'email', 'password1', 'password2')

    def clean_email(self):
        """Check for uniqueness of email"""
        email = self.cleaned_data.get('email')
        if User.objects.filter(email=email).exists():
            raise forms.ValidationError('User with this email already exists')
        return email
        
    def __init__(self, *args, **kwargs):
        super(UserRegistrationForm, self).__init__(*args, **kwargs)
        
        # Hints for fields
        self.fields['username'].help_text = 'Required field. No more than 150 characters. Only letters, numbers and @/./+/-/_.'
        self.fields['password1'].help_text = ('Password must be at least 8 characters long and contain letters and numbers. ' 
                                            'Should not be similar to your login.')
        self.fields['password2'].help_text = 'Enter the same password for verification.'

    def clean_password2(self):
        cd = self.cleaned_data
        if cd['password1'] != cd['password2']:
            raise forms.ValidationError('Passwords don\'t match.')
        return cd['password2']

