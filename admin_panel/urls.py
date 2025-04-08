from django.urls import path
from . import views

urlpatterns = [
    # Всі інші адреси крім кореневої (index прибраний, оскільки він тепер в core/urls.py)
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
    path('register/', views.register_view, name='register'),
    path('dashboard/', views.admin_panel_view, name='admin_panel'),
    # Channels
    path('channels-list/', views.channels_list_view, name='channels_list'),
    path('channel-create/', views.channel_create_view, name='channel_create'),
    path('channel-detail/<int:channel_id>/', views.channel_detail_view, name='channel_detail'),
    path('channel-update/<int:channel_id>/', views.channel_update_view, name='channel_update'),
    path('channel-delete/<int:channel_id>/', views.channel_delete_view, name='channel_delete'),
    # Categories
    path('categories-list/', views.categories_list_view, name='categories_list'),
    path('category-create/', views.category_create_view, name='category_create'),
    path('category-detail/<int:category_id>/', views.category_detail_view, name='category_detail'),
    path('category-update/<int:category_id>/', views.category_update_view, name='category_update'),
    path('category-delete/<int:category_id>/', views.category_delete_view, name='category_delete'),
    # Messages
    path('messages-list/', views.messages_list_view, name='messages_list'),
    path('message-detail/<int:message_id>/', views.message_detail_view, name='message_detail'),
    path('message-delete/<int:message_id>/', views.message_delete_view, name='message_delete'),
    # Telegram Sessions
    path('sessions-list/', views.sessions_list_view, name='sessions_list'),
    path('session-create/', views.session_create_view, name='session_create'),
    path('session-update/<int:session_id>/', views.session_update_view, name='session_update'),
    path('session-delete/<int:session_id>/', views.session_delete_view, name='session_delete'),
    path('auth-help/', views.auth_help_view, name='auth_help'),
]
