#!/usr/bin/env python3
"""
Окремий healthcheck сервер для Railway з базовою функціональністю
без залежностей від системних утиліт
"""
import os
import sys
import time
import logging
from http.server import HTTPServer, BaseHTTPRequestHandler

# Налаштовуємо логування
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger('health_server')

class HealthHandler(BaseHTTPRequestHandler):
    def _set_headers(self, status_code=200):
        """Встановлює заголовки відповіді"""
        self.send_response(status_code)
        self.send_header('Content-type', 'text/plain')
        self.end_headers()
    
    def _log_request(self):
        """Логує запит"""
        client_address = self.client_address[0]
        logger.info(f"Health request from {client_address}: {self.path}")
    
    def do_GET(self):
        """Обробляє GET запити"""
        self._log_request()
        
        # Перевіряємо стан сервісів без залежності від ps
        bot_status = self._check_bot_status()
        parser_status = self._check_parser_status()
        
        # Відповідь залежно від шляху
        if self.path in ['/health', '/healthz', '/health/', '/healthz/', '/ping']:
            self._set_headers()
            self.wfile.write(b"ok")
            return
        
        # Для статусного ендпоінту повертаємо більше інформації
        if self.path == '/status':
            self._set_headers()
            status = f"Bot: {bot_status}\nParser: {parser_status}\nTimestamp: {time.strftime('%Y-%m-%d %H:%M:%S')}\n"
            self.wfile.write(status.encode())
            return
        
        # За замовчуванням повертаємо 404
        self._set_headers(404)
        self.wfile.write(b"Not found")
    
    def _check_process_running(self, pid_file):
        """Перевіряє, чи процес запущений за PID файлом"""
        if not os.path.exists(pid_file):
            return "Not found"
            
        try:
            with open(pid_file, 'r') as f:
                pid = f.read().strip()
                
            if not pid:
                return "Empty PID"
                
            # Спроба перевірити процес через /proc (Linux)
            if os.path.exists(f"/proc/{pid}"):
                return "Running"
                
            # Спроба використати psutil, якщо доступний
            try:
                import psutil
                if psutil.pid_exists(int(pid)):
                    return "Running"
            except (ImportError, ValueError):
                pass
                
            return "Stopped"
        except Exception as e:
            logger.error(f"Error checking process: {e}")
            return f"Error: {str(e)}"
    
    def _check_bot_status(self):
        """Перевіряє статус бота"""
        return self._check_process_running('bot.pid')
    
    def _check_parser_status(self):
        """Перевіряє статус парсера"""
        return self._check_process_running('parser.pid')

def run_health_server(port=8081):
    """Запускає сервер здоров'я на вказаному порті"""
    try:
        # Створюємо сервер
        server_address = ('', port)
        httpd = HTTPServer(server_address, HealthHandler)
        logger.info(f"Starting health check server on port {port}")
        
        # Запускаємо сервер
        httpd.serve_forever()
    except Exception as e:
        logger.error(f"Error starting health server: {e}")
        sys.exit(1)

if __name__ == "__main__":
    # Отримуємо порт з середовища або використовуємо значення за замовчуванням
    port = int(os.environ.get('HEALTH_PORT', 8081))
    logger.info(f"Health server starting on port {port}")
    
    # Запускаємо сервер
    run_health_server(port) 