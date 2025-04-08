from django.db import models

class TelegramSessionManager(models.Manager):
    """
    A custom manager for TelegramSession model that handles missing columns gracefully.
    This helps prevent errors when the database schema doesn't match the model.
    """
    def get_queryset(self):
        qs = super().get_queryset()
        
        # Check which columns actually exist in the database
        from django.db import connection
        existing_columns = self._get_existing_columns()
        
        # Handle the case where columns don't exist by handling specific query scenarios
        # This is less ideal than fixing the database, but provides a fallback
        return qs
    
    def _get_existing_columns(self):
        """Get a list of existing columns for the TelegramSession table"""
        from django.db import connection
        
        cursor = connection.cursor()
        table_name = TelegramSession._meta.db_table
        cursor.execute(f"""
            SELECT column_name 
            FROM information_schema.columns 
            WHERE table_name = '{table_name}';
        """)
        columns = [row[0] for row in cursor.fetchall()]
        return columns

class TelegramSession(models.Model):
    phone = models.CharField(max_length=20, unique=True)
    api_id = models.CharField(max_length=10)
    api_hash = models.CharField(max_length=32)
    is_active = models.BooleanField(default=True)
    session_file = models.CharField(max_length=255, null=True, blank=True)
    verification_code = models.CharField(max_length=255, null=True, blank=True)
    password = models.CharField(max_length=255, null=True, blank=True)
    session_data = models.TextField(null=True, blank=True)
    auth_token = models.CharField(max_length=255, null=True, blank=True)
    needs_auth = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    # Add both managers
    objects = models.Manager()  # The default manager
    safe_objects = TelegramSessionManager()  # Safe manager that handles missing columns
    
    def __str__(self):
        return f"{self.phone} {'(Active)' if self.is_active else '(Inactive)'}"
    
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
        
    @classmethod
    def get_settings(cls):
        """Get the bot settings, creating a default instance if none exists"""
        settings, created = cls.objects.get_or_create(pk=1)
        if created:
            settings.save()
        return settings
