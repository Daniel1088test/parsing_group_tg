from django.urls import path
from .views import (
    index_view, login_view, logout_view, admin_panel_view,
    categories_list_view, category_create_view, category_detail_view, category_update_view, category_delete_view,
    categories_standalone_view,
    channels_list_view, channel_create_view, channel_detail_view, channel_update_view, channel_delete_view,
    messages_list_view, message_detail_view, message_delete_view,
    sessions_list_view, session_create_view, session_update_view, session_delete_view,
    authorize_session_view, register_view, bot_settings_view, run_migrations_view, auth_help_view
)

app_name = 'admin_panel'

urlpatterns = [
    path('', admin_panel_view, name='admin_panel'),
    path('login/', login_view, name='login'),
    path('register/', register_view, name='register'),
    path('logout/', logout_view, name='logout'),
    
    # Categories
    path('categories/', categories_list_view, name='categories_list'),
    path('categories/standalone/', categories_standalone_view, name='categories_standalone'),
    path('categories/create/', category_create_view, name='category_create'),
    path('categories/<int:category_id>/', category_detail_view, name='category_detail'),
    path('categories/<int:category_id>/update/', category_update_view, name='category_update'),
    path('categories/<int:category_id>/delete/', category_delete_view, name='category_delete'),
    
    # Channels
    path('channels/', channels_list_view, name='channels_list'),
    path('channels/create/', channel_create_view, name='channel_create'),
    path('channels/<int:channel_id>/', channel_detail_view, name='channel_detail'),
    path('channels/<int:channel_id>/update/', channel_update_view, name='channel_update'),
    path('channels/<int:channel_id>/delete/', channel_delete_view, name='channel_delete'),
    
    # Messages
    path('messages/', messages_list_view, name='messages_list'),
    path('messages/<int:message_id>/', message_detail_view, name='message_detail'),
    path('messages/<int:message_id>/delete/', message_delete_view, name='message_delete'),
    
    # Sessions
    path('sessions/', sessions_list_view, name='sessions_list'),
    path('sessions/create/', session_create_view, name='session_create'),
    path('sessions/<int:session_id>/update/', session_update_view, name='session_update'),
    path('sessions/<int:session_id>/delete/', session_delete_view, name='session_delete'),
    path('sessions/<int:session_id>/authorize/', authorize_session_view, name='authorize_session'),
    path('sessions/auth-help/', auth_help_view, name='auth_help'),
    path('run-migrations/', run_migrations_view, name='run_migrations'),
    
    # Bot settings
    path('settings/', bot_settings_view, name='bot_settings'),
]