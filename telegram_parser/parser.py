#!/usr/bin/env python3
"""
Модуль парсера Telegram - основна функціональність
"""
import logging
import time
import traceback
from admin_panel.models import TelegramSession, Channel, Category, Message

logger = logging.getLogger('telegram_parser.parser')

class TelegramParser:
    """Клас для парсингу повідомлень з каналів Telegram"""
    
    def __init__(self):
        """Ініціалізація парсера"""
        self.running = True
        self.sessions = []
        self.channels = []
        logger.info("Ініціалізовано об'єкт парсера")
    
    def load_sessions(self):
        """Завантаження активних сесій Telegram"""
        try:
            self.sessions = list(TelegramSession.objects.filter(is_active=True))
            logger.info(f"Завантажено {len(self.sessions)} активних сесій Telegram")
            return len(self.sessions) > 0
        except Exception as e:
            logger.error(f"Помилка при завантаженні сесій: {e}")
            return False
    
    def load_channels(self):
        """Завантаження активних каналів для парсингу"""
        try:
            self.channels = list(Channel.objects.filter(is_active=True).select_related('category', 'session'))
            logger.info(f"Завантажено {len(self.channels)} активних каналів")
            return len(self.channels) > 0
        except Exception as e:
            logger.error(f"Помилка при завантаженні каналів: {e}")
            return False
    
    def parse_channel(self, channel):
        """Парсинг одного каналу"""
        logger.info(f"Парсинг каналу: {channel.name} ({channel.url})")
        
        try:
            # Use the associated session or find an available one
            session = channel.session if hasattr(channel, 'session') and channel.session else None
            
            if not session:
                # If no session is assigned, try to find an available one
                available_sessions = [s for s in self.sessions if s.is_active]
                if available_sessions:
                    session = available_sessions[0]
                else:
                    logger.error(f"Немає доступних сесій для каналу {channel.name}")
                    return False
            
            # Import telethon here to avoid early import errors
            try:
                from telethon.sync import TelegramClient
                from telethon.errors import SessionPasswordNeededError, ChannelPrivateError
                from telethon.tl.functions.messages import GetHistoryRequest
                from telethon.tl.types import InputPeerChannel
            except ImportError as e:
                logger.error(f"Неможливо імпортувати бібліотеку Telethon: {e}")
                return False
                
            # Get session data
            api_id = session.api_id
            api_hash = session.api_hash
            phone = session.phone
            session_file = f"telethon_session_{phone.replace('+', '')}"
            
            # Create client
            client = None
            try:
                client = TelegramClient(session_file, api_id, api_hash)
                client.connect()
                
                # Check authorization
                if not client.is_user_authorized():
                    logger.error(f"Сесія не авторизована: {session_file}")
                    # Mark session as needing authentication
                    if hasattr(session, 'needs_auth'):
                        session.needs_auth = True
                        session.save()
                    return False
                
                # Get channel entity
                channel_entity = None
                try:
                    channel_entity = client.get_entity(channel.url)
                except Exception as e:
                    logger.error(f"Помилка отримання сутності каналу {channel.url}: {e}")
                    return False
                
                # Get messages
                messages = []
                try:
                    messages = client(GetHistoryRequest(
                        peer=channel_entity,
                        limit=50,  # Number of messages to retrieve
                        offset_date=None,
                        offset_id=0,
                        max_id=0,
                        min_id=0,
                        add_offset=0,
                        hash=0
                    ))
                except Exception as e:
                    logger.error(f"Помилка отримання повідомлень з каналу {channel.name}: {e}")
                    return False
                
                # Process messages
                message_count = 0
                for message in messages.messages:
                    if not message.message:
                        continue
                        
                    try:
                        # Check if message already exists
                        if Message.objects.filter(message_id=message.id, channel=channel).exists():
                            continue
                            
                        # Create new message
                        new_message = Message(
                            channel=channel,
                            message_id=message.id,
                            text=message.message,
                            date=message.date,
                            is_processed=False
                        )
                        new_message.save()
                        message_count += 1
                    except Exception as e:
                        logger.error(f"Помилка збереження повідомлення: {e}")
                
                logger.info(f"Збережено {message_count} нових повідомлень з каналу {channel.name}")
                return True
                
            except Exception as e:
                logger.error(f"Загальна помилка при роботі з Telethon: {e}")
                logger.error(traceback.format_exc())
                return False
            finally:
                if client:
                    client.disconnect()
        
        except Exception as e:
            logger.error(f"Помилка при парсингу каналу '{channel.name}': {e}")
            logger.error(traceback.format_exc())
            return False
    
    def run(self):
        """Запуск парсера для всіх каналів"""
        logger.info("Запуск парсингу каналів")
        
        # Завантажуємо сесії та канали
        if not self.load_sessions():
            logger.warning("Немає активних сесій Telegram. Парсер не запущено.")
            return False
            
        if not self.load_channels():
            logger.warning("Немає активних каналів для парсингу. Парсер не запущено.")
            return False
        
        try:
            # Обробляємо кожен канал
            for channel in self.channels:
                if not self.running:
                    break
                    
                try:
                    self.parse_channel(channel)
                except Exception as e:
                    logger.error(f"Помилка при парсингу каналу '{channel.name}': {e}")
                    logger.error(traceback.format_exc())
            
            logger.info("Парсинг каналів завершено")
            return True
            
        except Exception as e:
            logger.error(f"Загальна помилка при парсингу: {e}")
            logger.error(traceback.format_exc())
            return False 