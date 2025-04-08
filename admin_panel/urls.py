from django.urls import path
from . import views

urlpatterns = [
    path('', views.index_view, name='admin_panel'),
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
    path('channels/', views.channels_list_view, name='channels_list'),
    path('channels/add/', views.channel_create_view, name='channel_create'),
    path('channels/<int:channel_id>/edit/', views.channel_update_view, name='channel_update'),
    path('channels/<int:channel_id>/delete/', views.channel_delete_view, name='channel_delete'),
    path('channels/<int:channel_id>/', views.channel_detail_view, name='channel_detail'),
    path('categories/', views.categories_list_view, name='categories_list'),
    path('categories/add/', views.category_create_view, name='category_create'),
    path('categories/<int:category_id>/edit/', views.category_update_view, name='category_update'),
    path('categories/<int:category_id>/delete/', views.category_delete_view, name='category_delete'),
    path('categories/<int:category_id>/', views.category_detail_view, name='category_detail'),
    path('messages/', views.messages_list_view, name='messages_list'),
    path('messages/<int:message_id>/', views.message_detail_view, name='message_detail'),
    path('messages/<int:message_id>/delete/', views.message_delete_view, name='message_delete'),
    path('sessions/', views.sessions_list_view, name='sessions_list'),
    path('sessions/add/', views.session_create_view, name='session_create'),
    path('sessions/<int:session_id>/edit/', views.session_update_view, name='session_update'),
    path('sessions/<int:session_id>/delete/', views.session_delete_view, name='session_delete'),
    path('sessions/<int:session_id>/authorize/', views.authorize_session_view, name='authorize_session'),
    path('auth-help/', views.auth_help_view, name='auth_help'),
]