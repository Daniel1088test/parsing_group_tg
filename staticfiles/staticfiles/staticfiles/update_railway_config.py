#!/usr/bin/env python3
"""
Скрипт для оновлення конфігурації на сервері Railway для роботи з новим ботом.
Цей скрипт змінює налаштування посилань і деплоїть їх
"""
import os
import sys
import logging
import re
import time
import django

# Налаштування логування
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Ім'я користувача нового бота (важливо використовувати точну назву з @BotFather)
BOT_USERNAME = "chan_parsing_mon_bot"
BOT_TOKEN = "8102516142:AAFTsVXXujHHKoX2KZGqZXBHPBznfgh7kg0"

def init_django():
    """Ініціалізація Django"""
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
    try:
        django.setup()
        logger.info("Django ініціалізовано успішно")
        return True
    except Exception as e:
        logger.error(f"Помилка ініціалізації Django: {e}")
        return False

def update_environment_variables():
    """Оновлює змінні середовища"""
    os.environ['BOT_USERNAME'] = BOT_USERNAME
    os.environ['BOT_TOKEN'] = BOT_TOKEN
    logger.info(f"Змінні середовища оновлено: BOT_USERNAME={BOT_USERNAME}")

def update_config_files():
    """Оновлює конфігураційні файли"""
    files_updated = 0
    
    # 1. Оновлюємо .env файл
    if os.path.exists('.env'):
        try:
            with open('.env', 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Оновлюємо BOT_USERNAME
            updated_content = re.sub(r'BOT_USERNAME=.*', f'BOT_USERNAME={BOT_USERNAME}', content)
            
            with open('.env', 'w', encoding='utf-8') as f:
                f.write(updated_content)
            
            logger.info("✓ Файл .env оновлено")
            files_updated += 1
        except Exception as e:
            logger.error(f"Помилка оновлення .env: {e}")
    
    # 2. Оновлюємо tg_bot/config.py
    config_path = os.path.join('tg_bot', 'config.py')
    if os.path.exists(config_path):
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Оновлюємо BOT_USERNAME
            updated_content = re.sub(
                r'BOT_USERNAME\s*=\s*os\.environ\.get\([\'"]BOT_USERNAME[\'"]\s*,\s*[\'"].*?[\'"]\)',
                f'BOT_USERNAME = os.environ.get(\'BOT_USERNAME\', "{BOT_USERNAME}")',
                content
            )
            
            with open(config_path, 'w', encoding='utf-8') as f:
                f.write(updated_content)
            
            logger.info(f"✓ Файл {config_path} оновлено")
            files_updated += 1
        except Exception as e:
            logger.error(f"Помилка оновлення {config_path}: {e}")
    
    # 3. Оновлюємо templates/admin_panel/authorize_session.html
    template_path = os.path.join('templates', 'admin_panel', 'authorize_session.html')
    if os.path.exists(template_path):
        try:
            with open(template_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Змініть будь-яке хардкодоване посилання на бота
            if 'https://t.me/' in content:
                updated_content = re.sub(
                    r'https://t\.me/[^/\?\"\']+\?start=',
                    '{{ deep_link }}',
                    content
                )
                
                with open(template_path, 'w', encoding='utf-8') as f:
                    f.write(updated_content)
                
                logger.info(f"✓ Файл {template_path} оновлено")
                files_updated += 1
        except Exception as e:
            logger.error(f"Помилка оновлення {template_path}: {e}")
    
    # 4. Оновлюємо всі інші Python файли з посиланнями на бота
    for root, _, files in os.walk('.'):
        for file in files:
            if not file.endswith('.py') or file == 'update_railway_config.py':
                continue
                
            file_path = os.path.join(root, file)
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                if 'chan_parsing_mon_bot' in content:
                    updated_content = content.replace('chan_parsing_mon_bot', BOT_USERNAME)
                    updated_content = updated_content.replace('channel_pars_mode_bot', BOT_USERNAME)
                    
                    with open(file_path, 'w', encoding='utf-8') as f:
                        f.write(updated_content)
                    
                    logger.info(f"✓ Оновлено посилання на бота в {file_path}")
                    files_updated += 1
            except Exception as e:
                logger.error(f"Помилка оновлення {file_path}: {e}")
    
    return files_updated

def update_database_settings():
    """Оновлює налаштування в базі даних"""
    try:
        # Імпортуємо моделі після ініціалізації Django
        from admin_panel.models import BotSettings
        
        # Отримуємо або створюємо налаштування бота
        bot_settings = BotSettings.objects.first()
        if bot_settings:
            bot_settings.bot_token = BOT_TOKEN
            bot_settings.bot_username = BOT_USERNAME
            bot_settings.save()
            logger.info(f"✓ Налаштування бота оновлено в базі даних: {BOT_USERNAME}")
            return True
        else:
            # Створюємо нові налаштування
            BotSettings.objects.create(
                bot_token=BOT_TOKEN,
                bot_username=BOT_USERNAME,
                bot_name="Channel Parser Bot"
            )
            logger.info(f"✓ Створено нові налаштування бота в базі даних: {BOT_USERNAME}")
            return True
    except Exception as e:
        logger.error(f"Помилка оновлення налаштувань у базі даних: {e}")
        return False

def restart_bot():
    """Перезапускає бота"""
    logger.info("Перезапуск бота...")
    
    # Перевіряємо наявність скриптів для запуску
    scripts = ['direct_bot_runner.py', 'run_bot.py']
    for script in scripts:
        if os.path.exists(script):
            try:
                if sys.platform == 'win32':
                    import subprocess
                    subprocess.Popen(
                        [sys.executable, script],
                        creationflags=subprocess.CREATE_NEW_PROCESS_GROUP | subprocess.DETACHED_PROCESS,
                        env=os.environ.copy()
                    )
                else:
                    os.system(f"nohup python {script} > bot.log 2>&1 &")
                
                logger.info(f"✓ Бот перезапущено з використанням {script}")
                return True
            except Exception as e:
                logger.error(f"Помилка запуску {script}: {e}")
    
    logger.error("Жоден зі скриптів запуску не знайдено")
    return False

def main():
    """Основна функція"""
    logger.info("=== Початок оновлення конфігурації для нового бота ===")
    
    # Оновлюємо змінні середовища
    update_environment_variables()
    
    # Ініціалізуємо Django
    if not init_django():
        logger.warning("Продовжуємо без ініціалізації Django")
    
    # Оновлюємо конфігураційні файли
    files_updated = update_config_files()
    logger.info(f"Оновлено {files_updated} файлів")
    
    # Оновлюємо налаштування в базі даних
    db_updated = update_database_settings()
    
    # Перезапускаємо бота
    bot_restarted = restart_bot()
    
    # Підсумовуємо результати
    if files_updated > 0 and db_updated and bot_restarted:
        logger.info("=== Конфігурацію успішно оновлено для нового бота ===")
    else:
        logger.warning("=== Конфігурацію оновлено частково ===")
    
    logger.info(f"Новий бот: @{BOT_USERNAME}")

if __name__ == "__main__":
    main()
    sys.exit(0) 