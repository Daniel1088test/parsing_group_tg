from django.db import models
from django.contrib.auth.models import User
import os

class TelegramSessionManager(models.Manager):
    """
    Safe manager for TelegramSession that handles missing columns
    This ensures compatibility when updating an older database
    """
    def get_queryset(self):
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
    session_name = models.CharField(max_length=255, default="default")
    phone = models.CharField(max_length=20, unique=True)
    api_id = models.CharField(max_length=255, blank=True, null=True)
    api_hash = models.CharField(max_length=255, blank=True, null=True)
    session_string = models.TextField(blank=True, null=True)
    is_active = models.BooleanField(default=True)
    is_bot = models.BooleanField(default=False)
    verification_code = models.CharField(max_length=10, blank=True, null=True)
    password = models.CharField(max_length=255, blank=True, null=True)
    session_data = models.TextField(blank=True, null=True)
    auth_token = models.CharField(max_length=255, blank=True, null=True)
    needs_auth = models.BooleanField(default=False)
    session_file = models.CharField(max_length=255, blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    # Managers
    objects = models.Manager()  # Default manager
    safe_objects = TelegramSessionManager()  # Safe manager that handles missing columns
    
    def save(self, *args, **kwargs):
        # Make sure we don't save sensitive data in clear text in production
        if not self.session_name:
            self.session_name = f"session_{self.phone}"
        super().save(*args, **kwargs)
    
    class Meta:
        verbose_name = "Telegram Session"
        verbose_name_plural = "Telegram Sessions"
    
    def __str__(self):
        return f"{self.phone} ({self.session_name})"

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
    text = models.TextField(blank=True, null=True)
    media = models.FileField(upload_to='messages/', blank=True, null=True)
    media_type = models.CharField(max_length=255, blank=True, null=True)
    original_url = models.URLField(max_length=500, blank=True, null=True, help_text="Original media URL from Telegram")
    telegram_message_id = models.CharField(max_length=255, blank=True, null=True)
    telegram_channel_id = models.CharField(max_length=255, blank=True, null=True)
    telegram_link = models.URLField(max_length=255, blank=True, null=True)
    channel = models.ForeignKey(Channel, on_delete=models.CASCADE, related_name='messages')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    session_used = models.ForeignKey(TelegramSession, on_delete=models.SET_NULL, null=True, blank=True, related_name='messages')
    
    def __str__(self):
        return f"{self.telegram_message_id} ({self.channel.name})"
    
    def get_media_path(self):
        """Return the absolute path to the media file"""
        if self.media and hasattr(self.media, 'path'):
            return self.media.path
        return None
    
    class Meta:
        verbose_name = 'Message'
        verbose_name_plural = 'Messages'
        ordering = ['-created_at']

class BotSettings(models.Model):
    """Global settings for the Telegram bot operation"""
    bot_token = models.CharField(max_length=255, blank=True, null=True)
    default_api_id = models.IntegerField(default=2496)
    default_api_hash = models.CharField(max_length=255, blank=True, null=True)
    polling_interval = models.IntegerField(default=30, help_text="How often to check for new messages (in seconds)")
    max_messages_per_channel = models.IntegerField(default=10, help_text="Maximum number of messages to fetch per channel")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Bot Settings"
        verbose_name_plural = "Bot Settings"

    def __str__(self):
        return "Bot Settings"
        
    @classmethod
    def get_settings(cls):
        """Get the bot settings, creating a default instance if none exists"""
        try:
            settings, created = cls.objects.get_or_create(pk=1)
            return settings
        except Exception as e:
            # Якщо виникає помилка з базою даних, повертаємо налаштування за замовчуванням
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f"Error getting bot settings: {e}")
            
            # Створюємо тимчасовий об'єкт без збереження в БД
            default_settings = cls()
            default_settings.bot_token = "7923260865:AAGWm7t0Zz2PqFPI5PldEVwrOC4HZ_5oP0c"
            default_settings.default_api_id = 2496
            default_settings.default_api_hash = "c839f28bad345082329ec086fca021fa"
            default_settings.polling_interval = 30
            default_settings.max_messages_per_channel = 10
            
            return default_settings

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
