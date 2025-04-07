from django.db import models

class TelegramSession(models.Model):
    phone = models.CharField(max_length=20, unique=True)
    phone_hash = models.CharField(max_length=100, blank=True, null=True)
    session_string = models.TextField(blank=True, null=True)
    api_id = models.IntegerField(default=0)
    api_hash = models.CharField(max_length=100, blank=True, null=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    user_id = models.BigIntegerField(blank=True, null=True)
    session_file = models.CharField(max_length=255, blank=True, null=True)

    def __str__(self):
        return f"Session {self.phone}"

    class Meta:
        verbose_name = 'Telegram Session'
        verbose_name_plural = 'Telegram Sessions'
        ordering = ['-created_at']

class Category(models.Model):
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)
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
    name = models.CharField(max_length=100)
    url = models.CharField(max_length=200)
    category = models.ForeignKey(Category, on_delete=models.SET_NULL, null=True, blank=True)
    session = models.ForeignKey(TelegramSession, on_delete=models.SET_NULL, null=True, blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        session_info = f" ({self.session.phone})" if self.session else ""
        return f"{self.name} - {self.category.name}{session_info}"
    
    class Meta:
        verbose_name = 'Channel'
        verbose_name_plural = 'Channels'
        ordering = ['name']
    
class Message(models.Model):
    text = models.TextField(blank=True, null=True)
    media = models.CharField(max_length=255, blank=True, null=True)
    media_type = models.CharField(max_length=20, blank=True, null=True)
    telegram_message_id = models.BigIntegerField(null=True, blank=True)
    telegram_channel_id = models.BigIntegerField(null=True, blank=True)
    telegram_link = models.CharField(max_length=255, blank=True, null=True)
    channel = models.ForeignKey(Channel, on_delete=models.CASCADE)
    session_used = models.ForeignKey(TelegramSession, on_delete=models.SET_NULL, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Message {self.telegram_message_id} from {self.channel.name}"
    
    class Meta:
        verbose_name = 'Message'
        verbose_name_plural = 'Messages'
        ordering = ['created_at']
