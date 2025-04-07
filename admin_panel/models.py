from django.db import models

class TelegramSession(models.Model):
    phone = models.CharField(max_length=20, unique=True)
    api_id = models.CharField(max_length=255)
    api_hash = models.CharField(max_length=255)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    session_file = models.CharField(max_length=255, blank=True, null=True)
    session_data = models.TextField(blank=True, null=True, help_text="Base64 encoded session data")

    def __str__(self):
        return f"{self.phone} - {'Active' if self.is_active else 'Inactive'}"

    class Meta:
        verbose_name = 'Telegram Session'
        verbose_name_plural = 'Telegram Sessions'
        ordering = ['-created_at']

class Category(models.Model):
    name = models.CharField(max_length=255)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    session = models.ForeignKey(TelegramSession, on_delete=models.SET_NULL, null=True, blank=True, related_name='categories')

    def __str__(self):
        return self.name
    
    class Meta:
        verbose_name = 'Category'
        verbose_name_plural = 'Categories'
        ordering = ['name']
    
class Channel(models.Model):
    name = models.CharField(max_length=255)
    url = models.URLField(max_length=255, blank=True)
    telegram_id = models.CharField(max_length=255, blank=True, null=True, help_text="Telegram channel ID")
    telegram_username = models.CharField(max_length=255, blank=True, null=True, help_text="Telegram username (without @)")
    title = models.CharField(max_length=255, blank=True, null=True, help_text="Official channel title from Telegram")
    category = models.ForeignKey(Category, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    is_active = models.BooleanField(default=True)
    session = models.ForeignKey(TelegramSession, on_delete=models.SET_NULL, null=True, blank=True, related_name='channels')

    def __str__(self):
        display_name = self.title or self.name
        category_info = f" - {self.category.name}" if self.category else ""
        session_info = f" (via {self.session.phone})" if self.session else ""
        return f"{display_name}{category_info}{session_info}"
    
    def display_name(self):
        return self.title or self.name
    
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
        text_preview = self.text[:30] + "..." if len(self.text) > 30 else self.text
        return f"{self.channel.display_name()} - {text_preview}"
    
    class Meta:
        verbose_name = 'Message'
        verbose_name_plural = 'Messages'
        ordering = ['-created_at']
