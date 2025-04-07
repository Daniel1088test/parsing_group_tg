from django.contrib import admin
from .models import Category, Channel, Message, TelegramSession

# Sessions admin
class TelegramSessionAdmin(admin.ModelAdmin):
    list_display = ('phone', 'is_active', 'session_file', 'created_at')
    list_filter = ('is_active',)
    search_fields = ('phone',)
    readonly_fields = ('created_at', 'updated_at')

# Category admin with session filtering
class CategoryAdmin(admin.ModelAdmin):
    list_display = ('name', 'get_session_phone', 'channel_count', 'created_at')
    list_filter = ('session',)
    search_fields = ('name',)
    readonly_fields = ('created_at', 'updated_at')
    
    def get_session_phone(self, obj):
        return obj.session.phone if obj.session else "No session"
    get_session_phone.short_description = 'Session'
    
    def channel_count(self, obj):
        return obj.channels.count()
    channel_count.short_description = 'Channels'

# Channel admin with session filtering
class ChannelAdmin(admin.ModelAdmin):
    list_display = ('name', 'url', 'category', 'get_session_phone', 'is_active')
    list_filter = ('is_active', 'category', 'session')
    search_fields = ('name', 'url')
    readonly_fields = ('created_at', 'updated_at')
    
    def get_session_phone(self, obj):
        return obj.session.phone if obj.session else "No session"
    get_session_phone.short_description = 'Session'

# Message admin with enhanced filtering
class MessageAdmin(admin.ModelAdmin):
    list_display = ('short_text', 'channel', 'media_type', 'get_session_used', 'created_at')
    list_filter = ('channel', 'media_type', 'session_used')
    search_fields = ('text', 'channel__name')
    readonly_fields = ('created_at', 'updated_at', 'telegram_message_id', 'telegram_channel_id', 'telegram_link')
    
    def short_text(self, obj):
        return f"{obj.text[:50]}..." if len(obj.text) > 50 else obj.text
    short_text.short_description = 'Message Text'
    
    def get_session_used(self, obj):
        return obj.session_used.phone if obj.session_used else "Default"
    get_session_used.short_description = 'Session Used'

# Register models with custom admin classes
admin.site.register(TelegramSession, TelegramSessionAdmin)
admin.site.register(Category, CategoryAdmin)
admin.site.register(Channel, ChannelAdmin)
admin.site.register(Message, MessageAdmin)

