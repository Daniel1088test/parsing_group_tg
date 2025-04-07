from django.urls import path
from . import views

urlpatterns = [
    path('', views.index_view, name='index'),
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
    path('register/', views.register_view, name='register'),
    path('admin-panel/', views.admin_panel_view, name='admin_panel'),
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
]
