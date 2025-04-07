from django.db import models
from django.utils import timezone

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
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    session = models.ForeignKey(TelegramSession, on_delete=models.SET_NULL, null=True, blank=True, related_name='categories')

    def __str__(self):
        return self.name
    
    class Meta:
        verbose_name = "Category"
        verbose_name_plural = "Categories"
        ordering = ['name']
    
class Channel(models.Model):
    name = models.CharField(max_length=100)
    url = models.CharField(max_length=100, unique=True)
    description = models.TextField(blank=True)
    category = models.ForeignKey(Category, on_delete=models.CASCADE, related_name='channels')
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    last_parsed = models.DateTimeField(null=True, blank=True)
    telegram_id = models.CharField(max_length=255, blank=True, null=True, help_text="Telegram channel ID")
    telegram_username = models.CharField(max_length=255, blank=True, null=True, help_text="Telegram username (without @)")
    title = models.CharField(max_length=255, blank=True, null=True, help_text="Official channel title from Telegram")
    session = models.ForeignKey(TelegramSession, on_delete=models.SET_NULL, null=True, blank=True, related_name='channels')

    def __str__(self):
        display_name = self.title or self.name
        category_info = f" - {self.category.name}" if self.category else ""
        session_info = f" (via {self.session.phone})" if self.session else ""
        return f"{display_name}{category_info}{session_info}"
    
    def display_name(self):
        return self.title or self.name
    
    class Meta:
        verbose_name = "Channel"
        verbose_name_plural = "Channels"
        ordering = ['name']
    
class Message(models.Model):
    channel = models.ForeignKey(Channel, on_delete=models.CASCADE, related_name='messages')
    message_id = models.BigIntegerField()
    date = models.DateTimeField()
    text = models.TextField(blank=True)
    has_image = models.BooleanField(default=False)
    has_video = models.BooleanField(default=False)
    has_audio = models.BooleanField(default=False)
    has_document = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    session_used = models.ForeignKey(TelegramSession, on_delete=models.SET_NULL, null=True, blank=True, related_name='messages')

    def __str__(self):
        text_preview = self.text[:30] + "..." if len(self.text) > 30 else self.text
        return f"{self.channel.display_name()} - {text_preview}"
    
    class Meta:
        verbose_name = "Message"
        verbose_name_plural = "Messages"
        unique_together = ('channel', 'message_id')
        indexes = [
            models.Index(fields=['channel', 'date']),
            models.Index(fields=['message_id']),
        ]
