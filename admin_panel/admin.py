from django.contrib import admin
from .models import Category, Channel, Message, TelegramSession, BotSettings

@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ('name', 'created_at', 'updated_at')
    search_fields = ('name',)

@admin.register(Channel)
class ChannelAdmin(admin.ModelAdmin):
    list_display = ('name', 'url', 'category', 'session', 'is_active', 'created_at')
    list_filter = ('category', 'is_active', 'session')
    search_fields = ('name', 'url')

@admin.register(Message)
class MessageAdmin(admin.ModelAdmin):
    list_display = ('id', 'channel', 'created_at', 'media_type')
    list_filter = ('channel', 'channel__category', 'media_type')
    search_fields = ('text', 'channel__name')
    date_hierarchy = 'created_at'
    raw_id_fields = ('channel',)

@admin.register(TelegramSession)
class TelegramSessionAdmin(admin.ModelAdmin):
    list_display = ('phone', 'is_active', 'needs_auth', 'created_at')
    list_filter = ('is_active', 'needs_auth')
    search_fields = ('phone',)
    
    def get_fieldsets(self, request, obj=None):
        """Dynamically determine fields to show based on what's available in the model"""
        from django.apps import apps
        # Get the model fields
        model = apps.get_model('admin_panel', 'TelegramSession')
        field_names = [field.name for field in model._meta.get_fields()]
        
        # Group fields in logical sections
        basic_fields = ['phone', 'is_active', 'needs_auth']
        api_fields = ['api_id', 'api_hash']
        auth_fields = []
        extra_fields = []
        
        # Add fields if they exist in the model
        if 'verification_code' in field_names:
            auth_fields.append('verification_code')
        if 'password' in field_names:
            auth_fields.append('password')
        if 'auth_token' in field_names:
            auth_fields.append('auth_token')
        if 'session_file' in field_names:
            extra_fields.append('session_file')
        if 'session_data' in field_names:
            extra_fields.append('session_data')
        
        fieldsets = [
            ('Basic Info', {'fields': basic_fields}),
            ('API Configuration', {'fields': api_fields}),
        ]
        
        if auth_fields:
            fieldsets.append(('Authentication', {'fields': auth_fields, 'classes': ['collapse']}))
        
        if extra_fields:
            fieldsets.append(('Advanced Settings', {'fields': extra_fields, 'classes': ['collapse']}))
            
        return fieldsets

@admin.register(BotSettings)
class BotSettingsAdmin(admin.ModelAdmin):
    list_display = ('__str__', 'updated_at')
    
    def has_add_permission(self, request):
        # Only allow one instance of settings
        return not BotSettings.objects.exists()

