from django.db import models
from django.contrib.auth.models import User
import os
from django.conf import settings

class TelegramSessionManager(models.Manager):
    """
    Safe manager for TelegramSession that handles missing columns
    This ensures compatibility when updating an older database
    """
    def get_queryset(self):
        """Safe manager for TelegramSession that handles missing columns"""
        qs = super().get_queryset().only(
            "id", "phone", "is_active", "session_file", "created_at", "updated_at"
        )
        return qs
        qs = super().get_queryset()
        return qs

class Channel(models.Model):
    """Legacy Channel model for compatibility"""
    name = models.CharField(max_length=255)
    url = models.URLField(max_length=255)
    category = models.ForeignKey('Category', on_delete=models.CASCADE, related_name='channels')
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    session = models.ForeignKey('TelegramSession', on_delete=models.SET_NULL, null=True, blank=True)
    
    class Meta:
        verbose_name = 'Channel'
        verbose_name_plural = 'Channels'
        ordering = ['-created_at']
    
    def __str__(self):
        return self.name

class TelegramSession(models.Model):
    """Telegram session model for storing session data"""
    session_name = models.CharField(max_length=255, default='default')
    phone = models.CharField(max_length=20, unique=True, verbose_name="Номер телефону")
    api_id = models.CharField(max_length=20, blank=True, null=True, verbose_name="API ID")
    api_hash = models.CharField(max_length=100, blank=True, null=True, verbose_name="API Hash")
    session_string = models.TextField(verbose_name="Рядок сесії", blank=True, null=True)
    is_active = models.BooleanField(default=True, verbose_name="Активна")
    is_bot = models.BooleanField(default=False, verbose_name="Це бот")
    is_authorized = models.BooleanField(default=False, verbose_name="Авторизована")
    verification_code = models.CharField(max_length=10, blank=True, null=True)
    password = models.CharField(max_length=255, blank=True, null=True)
    session_data = models.TextField(blank=True, null=True, help_text="Encoded session data for persistent storage")
    auth_token = models.CharField(max_length=255, blank=True, null=True, help_text="Token for authorizing this session via bot")
    username = models.CharField(max_length=255, blank=True, null=True)
    phone_code_hash = models.CharField(max_length=255, blank=True, null=True)
    needs_auth = models.BooleanField(default=True, help_text="Indicates if this session needs to be authorized")
    session_file = models.CharField(max_length=255, blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        status = "Active" if self.is_active else "Inactive"
        auth_status = " (Needs Auth)" if self.needs_auth else ""
        auth_status = " (Authorized)" if self.is_authorized else auth_status
        return f"{self.phone} - {status}{auth_status} {'(Bot)' if self.is_bot else ''}"
    
    class Meta:
        verbose_name = "Telegram сесія"
        verbose_name_plural = "Telegram сесії"
        ordering = ['-created_at']
        db_table = "admin_panel_telegramsession"

class Category(models.Model):
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True, null=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    session = models.ForeignKey(TelegramSession, on_delete=models.SET_NULL, null=True, blank=True, related_name='categories')
    
    class Meta:
        verbose_name = 'Category'
        verbose_name_plural = 'Categories'
        ordering = ['name']
    
    def __str__(self):
        return self.name

class Message(models.Model):
    text = models.TextField()
    media = models.FileField(upload_to='messages/', null=True, blank=True)
    media_type = models.CharField(max_length=255, null=True, blank=True)
    original_url = models.URLField(max_length=500, null=True, blank=True, help_text="Original media URL from Telegram")
    telegram_message_id = models.CharField(max_length=255)
    telegram_channel_id = models.CharField(max_length=255)
    telegram_link = models.URLField(max_length=255)
    channel = models.ForeignKey(Channel, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    session_used = models.ForeignKey(TelegramSession, on_delete=models.SET_NULL, null=True, blank=True, related_name='messages')
    
    def __str__(self):
        return f"{self.telegram_message_id} - {self.text[:10]}"
    
    def save(self, *args, **kwargs):
        # If this is a new message with media, ensure correct permissions
        if self.pk is None and self.media:
            super().save(*args, **kwargs)
            # Set permissions on media file after saving
            try:
                import os
                media_path = self.media.path
                if os.path.exists(media_path):
                    os.chmod(media_path, 0o644)
            except Exception as e:
                # Don't let permission errors prevent saving
                print(f"Error setting file permissions: {e}")
        else:
            super().save(*args, **kwargs)
    
    class Meta:
        verbose_name = 'Message'
        verbose_name_plural = 'Messages'
        ordering = ['created_at']

class BotSettings(models.Model):
    """Model for bot settings"""
    bot_token = models.CharField(max_length=255, default="8102516142:AAFTsVXXujHHKoX2KZGqZXBHPBznfgh7kg0")
    bot_username = models.CharField(max_length=100, default="chan_parsing_mon_bot",
                                help_text="Bot username without @ symbol")
    bot_name = models.CharField(max_length=100, default="Channel Parser Bot", 
                               help_text="Display name of your bot")
    default_api_id = models.IntegerField(default=2496)
    default_api_hash = models.CharField(max_length=255, blank=True, null=True)
    polling_interval = models.IntegerField(default=30, help_text="How often to check for new messages (in seconds)")
    max_messages_per_channel = models.IntegerField(default=10, help_text="Maximum number of messages to fetch per channel")
    auth_guide_text = models.TextField(default="Please follow these steps to authorize your Telegram account",
                                     help_text="Text shown during authorization process")
    welcome_message = models.TextField(default="Welcome to the Channel Parser Bot. Use the menu below:",
                                     help_text="Welcome message shown to users")
    menu_style = models.CharField(max_length=20, choices=(
        ('default', 'Default Layout'),
        ('compact', 'Compact Layout'),
        ('expanded', 'Expanded Layout')
    ), default='default')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"Bot Settings (@{self.bot_username})"
    
    class Meta:
        verbose_name = 'Bot Settings'
        verbose_name_plural = 'Bot Settings'
        
    def save(self, *args, **kwargs):
        # Ensure only one instance exists
        if BotSettings.objects.exists() and not self.pk:
            raise ValueError("Only one Bot Settings instance can exist")
        return super().save(*args, **kwargs)
        
    @classmethod
    def get_settings(cls):
        """Get the single instance or create with defaults"""
        obj, created = cls.objects.get_or_create(pk=1)
        return obj

class TelegramChannel(models.Model):
    """Modern Telegram Channel model"""
    channel_id = models.CharField(max_length=255, unique=True)
    title = models.CharField(max_length=255)
    url = models.URLField(blank=True, null=True)
    description = models.TextField(blank=True, null=True)
    members_count = models.IntegerField(default=0)
    username = models.CharField(max_length=255, blank=True, null=True)
    avatar = models.ImageField(upload_to='channel_avatars/', blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = "Telegram Channel"
        verbose_name_plural = "Telegram Channels"
    
    def __str__(self):
        return self.title or self.channel_id
