from django.db import models

class TelegramSession(models.Model):
    phone = models.CharField(max_length=20, unique=True)
    api_id = models.CharField(max_length=255)
    api_hash = models.CharField(max_length=255)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    session_file = models.CharField(max_length=255, blank=True, null=True)
    needs_auth = models.BooleanField(default=True, help_text="Indicates if this session needs manual authentication")
    auth_token = models.CharField(max_length=255, blank=True, null=True, help_text="Token for authorizing this session via bot")

    def __str__(self):
        status = "Active" if self.is_active else "Inactive"
        auth_status = " (Needs Auth)" if self.needs_auth else ""
        return f"{self.phone} - {status}{auth_status}"

    class Meta:
        verbose_name = 'Telegram Session'
        verbose_name_plural = 'Telegram Sessions'
        ordering = ['-created_at']

class Category(models.Model):
    name = models.CharField(max_length=255)
    description = models.TextField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    session = models.ForeignKey(TelegramSession, on_delete=models.SET_NULL, null=True, blank=True, related_name='categories')
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return self.name
    
    def save(self, *args, **kwargs):
        # Забезпечуємо наявність значення в полі description
        if self.description is None:
            self.description = ''
        super().save(*args, **kwargs)
    
    class Meta:
        verbose_name = 'Category'
        verbose_name_plural = 'Categories'
        ordering = ['name']
    
class Channel(models.Model):
    name = models.CharField(max_length=255)
    url = models.URLField(max_length=255)
    category = models.ForeignKey(Category, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    is_active = models.BooleanField(default=True)
    session = models.ForeignKey(TelegramSession, on_delete=models.SET_NULL, null=True, blank=True, related_name='channels')

    def __str__(self):
        session_info = f" ({self.session.phone})" if self.session else ""
        return f"{self.name} - {self.category.name}{session_info}"
    
    class Meta:
        verbose_name = 'Channel'
        verbose_name_plural = 'Channels'
        ordering = ['name']
    
class Message(models.Model):
    text = models.TextField()
    media = models.FileField(upload_to='messages/', null=True, blank=True)
    media_type = models.CharField(max_length=255, null=True, blank=True)
    telegram_message_id = models.CharField(max_length=255)
    telegram_channel_id = models.CharField(max_length=255)
    telegram_link = models.URLField(max_length=255)
    channel = models.ForeignKey(Channel, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    session_used = models.ForeignKey(TelegramSession, on_delete=models.SET_NULL, null=True, blank=True, related_name='messages')

    def __str__(self):
        return f"{self.telegram_message_id} - {self.text[:10]}"
    
    class Meta:
        verbose_name = 'Message'
        verbose_name_plural = 'Messages'
        ordering = ['created_at']

class BotSettings(models.Model):
    """Settings for the Telegram bot and authentication"""
    bot_username = models.CharField(max_length=100, default="Channels_hunt_bot", 
                                   help_text="Username of your Telegram bot (without @)")
    bot_name = models.CharField(max_length=100, default="Channel Parser Bot", 
                               help_text="Display name of your bot")
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
