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
        
        # Тут буде реалізація парсингу конкретного каналу
        # Поки що просто імітуємо роботу для виправлення помилки
        time.sleep(1)  # Імітація роботи
        
        return True
    
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