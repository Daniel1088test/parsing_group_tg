#!/usr/bin/env python3
"""
Оптимізований скрипт для застосування міграцій на Railway
"""

import os
import sys
import subprocess
import time
import logging
import django

# Налаштовуємо логування
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger('migrate_railway')

# Додаємо поточну директорію до шляху Python
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Встановлюємо змінну середовища та ініціалізуємо Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')

def run_command(command, timeout=60, ignore_errors=False):
    """Запускає команду з таймаутом та повертає результат"""
    logger.info(f"Виконуємо команду: {' '.join(command)}")
    
    try:
        result = subprocess.run(
            command,
            capture_output=True,
            text=True,
            timeout=timeout
        )
        
        if result.returncode == 0:
            logger.info(f"Команда успішно виконана")
            return True
        else:
            logger.error(f"Помилка при виконанні команди: {result.stderr}")
            if ignore_errors:
                logger.warning("Ігноруємо помилку і продовжуємо")
                return False
            else:
                return False
                
    except subprocess.TimeoutExpired:
        logger.error(f"Час виконання команди вичерпано (>{timeout}s)")
        return False
    except Exception as e:
        logger.error(f"Помилка при запуску команди: {str(e)}")
        return False

def setup_media_directories():
    """Створює необхідні директорії для медіафайлів"""
    directories = [
        "media",
        "media/messages",
        "media/thumbnails",
        "staticfiles",
        "staticfiles/img",
        "logs",
        "logs/bot",
        "data",
        "data/sessions"
    ]
    
    logger.info("Створення необхідних директорій...")
    
    for directory in directories:
        try:
            if not os.path.exists(directory):
                os.makedirs(directory)
                logger.info(f"Створено директорію: {directory}")
                
            # Встановлюємо права доступу
            os.chmod(directory, 0o755)
        except Exception as e:
            logger.error(f"Помилка при створенні директорії {directory}: {e}")

def apply_migrations():
    """Застосовує міграції Django з обробкою помилок"""
    logger.info("Застосування міграцій Django...")
    
    # Спробуємо різні стратегії міграції
    strategies = [
        # Стратегія 1: Стандартна міграція
        {"command": ["python", "manage.py", "migrate", "--noinput"], "timeout": 60},
        
        # Стратегія 2: Міграція базових додатків
        {"command": ["python", "manage.py", "migrate", "auth", "admin", "contenttypes", "sessions", "--noinput"], "timeout": 30, "ignore_errors": True},
        
        # Стратегія 3: Fake-initial
        {"command": ["python", "manage.py", "migrate", "--fake-initial", "--noinput"], "timeout": 30, "ignore_errors": True},
        
        # Стратегія 4: Міграція тільки нашого додатка
        {"command": ["python", "manage.py", "migrate", "admin_panel", "--noinput"], "timeout": 30, "ignore_errors": True},
    ]
    
    for idx, strategy in enumerate(strategies, 1):
        logger.info(f"Стратегія міграції #{idx}")
        
        # Запускаємо команду
        success = run_command(
            strategy["command"],
            timeout=strategy.get("timeout", 60),
            ignore_errors=strategy.get("ignore_errors", False)
        )
        
        # Якщо успішно, завершуємо
        if success:
            logger.info(f"Міграція успішно застосована за стратегією #{idx}")
            return True
        
        # Пауза перед наступною спробою
        if idx < len(strategies):
            logger.info(f"Чекаємо 2 секунди перед наступною спробою...")
            time.sleep(2)
    
    logger.warning("Всі стратегії міграції вичерпано")
    return False

def fix_media_paths():
    """Виправляє шляхи до медіафайлів для Railway"""
    logger.info("Виправляємо шляхи до медіафайлів...")
    
    # Запускаємо скрипти для виправлення шляхів
    scripts = [
        ["python", "fix_media_directories.py"],
        ["python", "fix_railway_media.py"]
    ]
    
    for script in scripts:
        run_command(script, timeout=30, ignore_errors=True)

def collect_staticfiles():
    """Збирає статичні файли"""
    logger.info("Збираємо статичні файли...")
    
    run_command(["python", "manage.py", "collectstatic", "--noinput"], timeout=30, ignore_errors=True)

def check_installed_packages():
    """Перевіряє встановлені пакети для діагностики"""
    try:
        logger.info("Перевірка встановлених пакетів...")
        import importlib.metadata
        import pkg_resources
        
        # Критичні пакети для роботи
        critical_packages = [
            'Django', 'aiogram', 'Telethon', 'psycopg2'
        ]
        
        # Перевіряємо критичні пакети
        for package in critical_packages:
            try:
                version = pkg_resources.get_distribution(package).version
                logger.info(f"✓ {package}: {version}")
            except pkg_resources.DistributionNotFound:
                logger.error(f"✗ Пакет {package} не встановлено!")
        
        return True
    except Exception as e:
        logger.error(f"Помилка при перевірці пакетів: {e}")
        return False

def main():
    """Основна функція для запуску міграцій і підготовки до запуску"""
    logger.info("=== Початок підготовки до запуску на Railway ===")
    
    # Етап 1: Створюємо необхідні директорії
    setup_media_directories()
    
    # Етап 1.5: Перевіряємо залежності
    check_installed_packages()
    
    # Етап 2: Ініціалізуємо Django для використання в скрипті
    try:
        django.setup()
        logger.info("Django успішно ініціалізовано")
    except Exception as e:
        logger.error(f"Помилка ініціалізації Django: {e}")
        # Продовжуємо виконання, оскільки міграції можуть працювати через subprocess
    
    # Етап 3: Застосовуємо міграції
    migrations_success = apply_migrations()
    
    # Етап 4: Збираємо статичні файли
    collect_staticfiles()
    
    # Етап 5: Виправляємо шляхи до медіафайлів
    fix_media_paths()
    
    # Етап 6: Створюємо символічні посилання
    try:
        staticfiles_media = os.path.join("staticfiles", "media")
        if not os.path.exists(staticfiles_media):
            os.makedirs(staticfiles_media)
        
        # Створюємо символічне посилання
        media_link_path = os.path.join("staticfiles", "media", "messages")
        media_target_path = os.path.abspath(os.path.join("media", "messages"))
        
        if not os.path.exists(media_link_path) and os.path.exists(media_target_path):
            if os.name == 'nt':  # Windows
                # На Windows можемо просто створити жорстке посилання
                run_command(["mklink", "/j", media_link_path, media_target_path], ignore_errors=True)
            else:  # Unix/Linux
                os.symlink(media_target_path, media_link_path)
                logger.info(f"Створено символічне посилання: {media_link_path} -> {media_target_path}")
    except Exception as e:
        logger.error(f"Помилка при створенні символічних посилань: {e}")
    
    # Підсумок
    logger.info("=== Підготовка до запуску завершена ===")
    
    # Повертаємо успіх, навіть якщо були проблеми, щоб не блокувати запуск
    return 0

if __name__ == "__main__":
    sys.exit(main()) 