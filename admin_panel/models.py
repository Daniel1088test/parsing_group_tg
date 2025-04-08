from django.db import models

class TelegramSession(models.Model):
    phone = models.CharField(max_length=15, unique=True)
    api_id = models.IntegerField(null=True, blank=True)
    api_hash = models.CharField(max_length=255, null=True, blank=True)
    is_active = models.BooleanField(default=True)
    session_file = models.CharField(max_length=255, null=True, blank=True)
    verification_code = models.CharField(max_length=10, null=True, blank=True)
    auth_token = models.CharField(max_length=100, null=True, blank=True)
    needs_auth = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.phone}"

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
