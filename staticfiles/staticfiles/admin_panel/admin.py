from django.contrib import admin
from .models import Category, Channel, Message, TelegramSession, BotSettings, TelegramChannel
import subprocess
import os
import sys
import logging
from django.http import HttpResponseRedirect
from django.urls import path
from django.contrib import messages

logger = logging.getLogger('admin_panel')

@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ('name', 'is_active', 'session', 'updated_at')
    list_filter = ('is_active', 'session')
    search_fields = ('name', 'description')

@admin.register(Channel)
class ChannelAdmin(admin.ModelAdmin):
    list_display = ('name', 'category', 'is_active', 'session', 'updated_at')
    list_filter = ('is_active', 'category', 'session')
    search_fields = ('name', 'url')
    readonly_fields = ('created_at', 'updated_at')

@admin.register(Message)
class MessageAdmin(admin.ModelAdmin):
    list_display = ('telegram_message_id', 'channel', 'created_at', 'media_type')
    list_filter = ('media_type', 'channel', 'created_at')
    search_fields = ('text', 'telegram_message_id', 'telegram_channel_id')
    readonly_fields = ('created_at', 'updated_at')

@admin.register(TelegramSession)
class TelegramSessionAdmin(admin.ModelAdmin):
    list_display = ('phone', 'session_name', 'is_active', 'is_bot', 'needs_auth', 'created_at')
    list_filter = ('is_active', 'is_bot', 'needs_auth')
    search_fields = ('phone', 'session_name')
    readonly_fields = ('created_at', 'updated_at')
    fieldsets = (
        ('Основна інформація', {
            'fields': ('phone', 'session_name', 'is_active', 'is_bot')
        }),
        ('API налаштування', {
            'fields': ('api_id', 'api_hash')
        }),
        ('Аутентифікація', {
            'fields': ('password', 'verification_code', 'needs_auth', 'auth_token')
        }),
        ('Сесійні дані', {
            'fields': ('session_string', 'session_data', 'session_file'),
            'classes': ('collapse',)
        }),
        ('Системна інформація', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )

@admin.register(BotSettings)
class BotSettingsAdmin(admin.ModelAdmin):
    list_display = ('bot_username', 'bot_name', 'has_token', 'updated_at')
    readonly_fields = ('created_at', 'updated_at')
    fieldsets = (
        ('Налаштування бота', {
            'fields': ('bot_username', 'bot_name', 'bot_token')
        }),
        ('API налаштування', {
            'fields': ('default_api_id', 'default_api_hash')
        }),
        ('Налаштування парсингу', {
            'fields': ('polling_interval', 'max_messages_per_channel')
        }),
        ('Інтерфейс', {
            'fields': ('auth_guide_text', 'welcome_message', 'menu_style')
        }),
        ('Системна інформація', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    def has_token(self, obj):
        return bool(obj.bot_token)
    has_token.boolean = True
    has_token.short_description = "Токен налаштовано"
    
    def has_add_permission(self, request):
        # Дозволяємо створити лише один об'єкт налаштувань
        return not BotSettings.objects.exists()
    
    def has_delete_permission(self, request, obj=None):
        # Забороняємо видалення об'єкту налаштувань
        return False
        
    def get_urls(self):
        urls = super().get_urls()
        custom_urls = [
            path('check_services/', self.admin_site.admin_view(self.check_services_view), name='check_services'),
            path('start_services/', self.admin_site.admin_view(self.start_services_view), name='start_services'),
        ]
        return custom_urls + urls
    
    def check_services_view(self, request):
        """Запускає скрипт перевірки сервісів"""
        try:
            script_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'check_services.py')
            if os.path.exists(script_path):
                result = subprocess.run(
                    [sys.executable, script_path],
                    capture_output=True,
                    text=True
                )
                
                if result.returncode == 0:
                    messages.success(request, "Перевірка сервісів успішно виконана")
                    for line in result.stdout.splitlines():
                        if 'запущено' in line.lower():
                            messages.info(request, line)
                else:
                    messages.error(request, f"Помилка при перевірці сервісів: {result.stderr}")
            else:
                messages.error(request, f"Скрипт перевірки сервісів не знайдено: {script_path}")
        except Exception as e:
            messages.error(request, f"Помилка: {str(e)}")
            
        return HttpResponseRedirect("../")
    
    def start_services_view(self, request):
        """Запускає скрипт запуску сервісів"""
        try:
            # Запускаємо перевірку та запуск сервісів
            script_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'check_services.py')
            if os.path.exists(script_path):
                # Робимо скрипт виконуваним
                os.chmod(script_path, 0o755)
                
                result = subprocess.run(
                    [sys.executable, script_path],
                    capture_output=True,
                    text=True
                )
                
                if result.returncode == 0:
                    messages.success(request, "Запуск сервісів успішно виконано")
                    for line in result.stdout.splitlines():
                        if 'запущено' in line.lower():
                            messages.info(request, line)
                else:
                    messages.error(request, f"Помилка при запуску сервісів: {result.stderr}")
            else:
                messages.error(request, f"Скрипт запуску сервісів не знайдено: {script_path}")
        except Exception as e:
            messages.error(request, f"Помилка: {str(e)}")
            
        return HttpResponseRedirect("../")

@admin.register(TelegramChannel)
class TelegramChannelAdmin(admin.ModelAdmin):
    list_display = ('title', 'username', 'members_count', 'updated_at')
    search_fields = ('title', 'username', 'channel_id')
    readonly_fields = ('created_at', 'updated_at')

