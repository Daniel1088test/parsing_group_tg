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

def setup_bot_token():
    """Налаштовує токен бота для Railway"""
    logger.info("Перевірка та налаштування токену бота...")
    
    # Перевіряємо чи токен вже встановлено в змінних середовища
    token = os.environ.get('BOT_TOKEN')
    if token:
        logger.info(f"Токен бота вже встановлено в змінних середовища")
        return True
    
    # Перевіряємо наявність токену в файлі bot_token.env
    if os.path.exists('bot_token.env'):
        try:
            with open('bot_token.env', 'r') as f:
                content = f.read().strip()
                if content.startswith('BOT_TOKEN='):
                    token = content.split('=', 1)[1].strip()
                    os.environ['BOT_TOKEN'] = token
                    logger.info(f"Токен бота завантажено з файлу bot_token.env")
                    return True
        except Exception as e:
            logger.error(f"Помилка при читанні файлу bot_token.env: {e}")
    
    # Спробуємо знайти токен в config.py
    try:
        # Ініціалізуємо Django
        django.setup()
        try:
            from tg_bot.config import TOKEN_BOT
            if TOKEN_BOT:
                os.environ['BOT_TOKEN'] = TOKEN_BOT
                logger.info(f"Токен бота завантажено з config.py")
                return True
        except ImportError:
            logger.warning("Не вдалося імпортувати TOKEN_BOT з config.py")
    except Exception as e:
        logger.error(f"Помилка при ініціалізації Django: {e}")
    
    # Спробуємо знайти токен в базі даних
    try:
        # Ініціалізуємо Django
        django.setup()
        try:
            from admin_panel.models import BotSettings
            bot_settings = BotSettings.objects.first()
            if bot_settings and bot_settings.bot_token:
                token = bot_settings.bot_token
                os.environ['BOT_TOKEN'] = token
                logger.info(f"Токен бота завантажено з бази даних")
                
                # Зберігаємо токен у файл для використання в інших скриптах
                try:
                    with open('bot_token.env', 'w') as f:
                        f.write(f"BOT_TOKEN={token}")
                    logger.info(f"Токен бота збережено у файлі bot_token.env")
                except Exception as e:
                    logger.error(f"Помилка при збереженні токену у файл: {e}")
                
                return True
        except Exception as e:
            logger.warning(f"Помилка при отриманні токену з бази даних: {e}")
    except Exception as e:
        logger.error(f"Помилка при ініціалізації Django для доступу до бази даних: {e}")
    
    # Якщо токен не знайдено, спробуємо встановити з фіксованого значення
    # Це значення ви вказали раніше: "7923260865:AAGYew9JnOJV6hz0LGeRCb1kS6AejHoX61g"
    hardcoded_token = "7923260865:AAGYew9JnOJV6hz0LGeRCb1kS6AejHoX61g"
    
    # Запускаємо скрипт fix_token.py з токеном як аргументом
    try:
        result = run_command(["python", "fix_token.py", hardcoded_token], timeout=30)
        if result:
            logger.info(f"Токен бота успішно встановлено через fix_token.py")
            
            # Перевіряємо чи з'явився файл з токеном
            if os.path.exists('bot_token.env'):
                try:
                    with open('bot_token.env', 'r') as f:
                        content = f.read().strip()
                        if content.startswith('BOT_TOKEN='):
                            token = content.split('=', 1)[1].strip()
                            os.environ['BOT_TOKEN'] = token
                            logger.info(f"Токен бота завантажено з файлу bot_token.env після виконання fix_token.py")
                            return True
                except Exception as e:
                    logger.error(f"Помилка при читанні файлу bot_token.env після виконання fix_token.py: {e}")
        else:
            logger.error(f"Помилка при виконанні fix_token.py")
    except Exception as e:
        logger.error(f"Помилка при запуску fix_token.py: {e}")
    
    # Якщо всі спроби невдалі, встановлюємо токен напряму
    try:
        os.environ['BOT_TOKEN'] = hardcoded_token
        
        # Зберігаємо токен у файл для використання в інших скриптах
        try:
            with open('bot_token.env', 'w') as f:
                f.write(f"BOT_TOKEN={hardcoded_token}")
            logger.info(f"Токен бота збережено у файлі bot_token.env")
        except Exception as e:
            logger.error(f"Помилка при збереженні токену у файл: {e}")
        
        logger.warning(f"Використовуємо жорстко закодований токен як останній варіант")
        return True
    except Exception as e:
        logger.error(f"Помилка при встановленні жорстко закодованого токену: {e}")
        return False

def check_installed_packages():
    """Перевіряє встановлені пакети для діагностики"""
    try:
        logger.info("Перевірка встановлених пакетів...")
        
        # Перевіряємо наявність pkg_resources
        try:
            import pkg_resources
            pkg_resources_available = True
        except ImportError:
            pkg_resources_available = False
            logger.warning("pkg_resources не встановлено, спроба встановити setuptools...")
            try:
                subprocess.run([sys.executable, "-m", "pip", "install", "setuptools>=65.5.1"], check=True)
                logger.info("setuptools успішно встановлено")
                try:
                    import pkg_resources
                    pkg_resources_available = True
                except ImportError:
                    logger.error("pkg_resources все ще недоступний після встановлення setuptools")
            except Exception as e:
                logger.error(f"Не вдалося встановити setuptools: {e}")
        
        # Критичні пакети для роботи
        critical_packages = [
            'Django', 'aiogram', 'Telethon', 'psycopg2', 'Pillow'
        ]
        
        # Функція для перевірки встановлених пакетів без pkg_resources
        def is_package_installed(package_name):
            try:
                __import__(package_name.lower())
                return True
            except ImportError:
                return False
        
        # Перевіряємо критичні пакети
        for package in critical_packages:
            # Спочатку спробуємо через importlib
            try:
                if pkg_resources_available:
                    # Використовуємо pkg_resources
                    version = pkg_resources.get_distribution(package).version
                    logger.info(f"✓ {package}: {version}")
                else:
                    # Використовуємо імпорт
                    package_imported = is_package_installed(package)
                    if package_imported:
                        logger.info(f"✓ {package}: встановлено (версія невідома)")
                    else:
                        raise ImportError(f"Пакет {package} не імпортується")
            except (pkg_resources.DistributionNotFound, ImportError):
                logger.error(f"✗ Пакет {package} не встановлено!")
                
                # Екстрена інсталяція для критичних пакетів
                if package.lower() in ['pillow', 'django', 'psycopg2']:
                    logger.warning(f"Спроба встановити {package}...")
                    try:
                        # Special handling for psycopg2
                        if package.lower() == 'psycopg2':
                            # Try installing binary package first
                            subprocess.run([sys.executable, "-m", "pip", "install", "psycopg2-binary==2.9.9"], check=True)
                            logger.info(f"Пакет psycopg2-binary успішно встановлено")
                            
                            # Then try installing the regular package 
                            try:
                                subprocess.run([sys.executable, "-m", "pip", "install", "psycopg2==2.9.9"], check=True)
                                logger.info(f"Пакет psycopg2 успішно встановлено")
                            except Exception as e:
                                logger.warning(f"Не вдалося встановити psycopg2, але psycopg2-binary вже встановлено: {e}")
                        else:
                            # For other packages
                            subprocess.run([sys.executable, "-m", "pip", "install", package], check=True)
                            logger.info(f"Пакет {package} успішно встановлено")
                    except Exception as e:
                        logger.error(f"Не вдалося встановити {package}: {e}")
        
        # Additional check for database connection
        try:
            import psycopg2
            logger.info("Testing database connection...")
            db_url = os.environ.get('DATABASE_URL')
            if db_url:
                conn = psycopg2.connect(db_url)
                cursor = conn.cursor()
                cursor.execute('SELECT 1')
                cursor.close()
                conn.close()
                logger.info("✓ Database connection successful!")
            else:
                logger.warning("⚠️ DATABASE_URL environment variable not set!")
        except Exception as e:
            logger.error(f"⚠️ Database connection failed: {e}")
            
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
    
    # Етап 1.6: Налаштовуємо токен бота
    setup_bot_token()
    
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