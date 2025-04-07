from django.contrib import admin
from .models import Channel, Category, Message, TelegramSession

# Sessions admin
@admin.register(TelegramSession)
class TelegramSessionAdmin(admin.ModelAdmin):
    list_display = ('phone', 'is_active', 'created_at', 'updated_at')
    list_filter = ('is_active',)
    search_fields = ('phone',)
    readonly_fields = ('created_at', 'updated_at')
    fieldsets = (
        (None, {
            'fields': ('phone', 'api_id', 'api_hash', 'is_active')
        }),
        ('Session Data', {
            'fields': ('session_file', 'session_data'),
            'classes': ('collapse',)
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )

# Category admin with session filtering
@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ('name', 'session', 'created_at', 'updated_at')
    list_filter = ('session',)
    search_fields = ('name',)
    readonly_fields = ('created_at', 'updated_at')
    fieldsets = (
        (None, {
            'fields': ('name', 'description', 'session')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )

# Channel admin with session filtering
@admin.register(Channel)
class ChannelAdmin(admin.ModelAdmin):
    list_display = ('name', 'category', 'is_active', 'session', 'created_at', 'updated_at')
    list_filter = ('category', 'is_active', 'session')
    search_fields = ('name', 'url')
    readonly_fields = ('created_at', 'updated_at', 'last_parsed')
    fieldsets = (
        (None, {
            'fields': ('name', 'url', 'description', 'category', 'is_active', 'session')
        }),
        ('Telegram Info', {
            'fields': ('telegram_id', 'telegram_username', 'title'),
            'classes': ('collapse',)
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at', 'last_parsed'),
            'classes': ('collapse',)
        }),
    )

# Message admin with enhanced filtering
@admin.register(Message)
class MessageAdmin(admin.ModelAdmin):
    list_display = ('channel', 'message_id', 'date', 'has_media', 'created_at')
    list_filter = ('channel', 'has_image', 'has_video', 'has_audio', 'has_document')
    search_fields = ('text', 'channel__name')
    readonly_fields = ('created_at', 'updated_at', 'message_id', 'date')
    
    def has_media(self, obj):
        """Check if message has any media"""
        return any([obj.has_image, obj.has_video, obj.has_audio, obj.has_document])
    has_media.boolean = True
    has_media.short_description = 'Has Media'
    
    fieldsets = (
        (None, {
            'fields': ('channel', 'message_id', 'date', 'text')
        }),
        ('Media Info', {
            'fields': ('has_image', 'has_video', 'has_audio', 'has_document'),
            'classes': ('collapse',)
        }),
        ('Session Info', {
            'fields': ('session_used',),
            'classes': ('collapse',)
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )

