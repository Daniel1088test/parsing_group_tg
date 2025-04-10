#!/usr/bin/env python3
"""
Скрипт для виправлення імені користувача бота у всіх конфігураційних файлах
"""
import os
import sys
import logging
import re
import subprocess

# Налаштування логування
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Налаштування бота
BOT_TOKEN = "8102516142:AAFTsVXXujHHKoX2KZGqZXBHPBznfgh7kg0"

# ВАЖЛИВО: Використовуємо правильне ім'я користувача, яке відображається в Telegram
# У вашому випадку це те, що показано в інтерфейсі Telegram як @Channels_hunt_bot
BOT_USERNAME = "Channels_hunt_bot"

def update_config_files():
    """Оновлює конфігураційні файли з правильним ім'ям користувача бота"""
    logger.info(f"Встановлюємо правильне ім'я користувача бота: {BOT_USERNAME}")
    
    # 1. Оновлюємо .env
    if os.path.exists('.env'):
        try:
            with open('.env', 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Оновлюємо BOT_USERNAME
            updated_content = re.sub(
                r'BOT_USERNAME=.*',
                f'BOT_USERNAME={BOT_USERNAME}',
                content
            )
            
            with open('.env', 'w', encoding='utf-8') as f:
                f.write(updated_content)
            
            logger.info("✓ Оновлено .env")
        except Exception as e:
            logger.error(f"Помилка оновлення .env: {e}")
    
    # 2. Оновлюємо config.py
    config_path = os.path.join('tg_bot', 'config.py')
    if os.path.exists(config_path):
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Виправляємо синтаксичні помилки і оновлюємо BOT_USERNAME
            updated_content = re.sub(
                r'BOT_USERNAME\s*=\s*os\.environ\.get\([\'"]BOT_USERNAME[\'"]\s*,\s*[\'"].*?[\'"]\)(?:\s*,[\'"].*?[\'"]\))?',
                f'BOT_USERNAME = os.environ.get(\'BOT_USERNAME\', "{BOT_USERNAME}")',
                content
            )
            
            with open(config_path, 'w', encoding='utf-8') as f:
                f.write(updated_content)
            
            logger.info(f"✓ Оновлено {config_path}")
        except Exception as e:
            logger.error(f"Помилка оновлення {config_path}: {e}")
    
    # 3. Оновлюємо всі інші Python файли з посиланнями на ім'я бота
    py_files_to_check = []
    for root, _, files in os.walk('.'):
        for file in files:
            if file.endswith('.py') and file not in ['fix_bot_username.py']:
                py_files_to_check.append(os.path.join(root, file))
    
    old_usernames = ['Channels_hunt_bot', 'Channels_hunt_bot', 'Channels_hunt_bot']
    for file_path in py_files_to_check:
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Перевіряємо, чи є посилання на старі імена
            if any(name in content for name in old_usernames):
                # Оновлюємо всі змінні BOT_USERNAME
                updated_content = re.sub(
                    r'(BOT_USERNAME\s*=\s*[\'"])(Channels_hunt_bot|Channels_hunt_bot)([\'"])',
                    f'\\1{BOT_USERNAME}\\3',
                    content
                )
                
                # Оновлюємо всі рядки з новими іменами
                for old_name in old_usernames:
                    if old_name != BOT_USERNAME and old_name in updated_content:
                        updated_content = updated_content.replace(f'"{old_name}"', f'"{BOT_USERNAME}"')
                        updated_content = updated_content.replace(f"'{old_name}'", f"'{BOT_USERNAME}'")
                
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(updated_content)
                
                logger.info(f"✓ Оновлено {file_path}")
        except Exception as e:
            logger.error(f"Помилка оновлення {file_path}: {e}")

def update_database():
    """Оновлює налаштування в базі даних"""
    try:
        # Ініціалізуємо Django
        os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
        import django
        django.setup()
        
        # Імпортуємо моделі
        from admin_panel.models import BotSettings
        
        # Оновлюємо або створюємо налаштування бота
        bot_settings = BotSettings.objects.first()
        if bot_settings:
            bot_settings.bot_token = BOT_TOKEN
            bot_settings.bot_username = BOT_USERNAME
            bot_settings.save()
            logger.info("✓ Оновлено налаштування бота в базі даних")
        else:
            BotSettings.objects.create(
                bot_token=BOT_TOKEN,
                bot_username=BOT_USERNAME,
                bot_name="Channel Parser Bot"
            )
            logger.info("✓ Створено нові налаштування бота в базі даних")
    except Exception as e:
        logger.error(f"Помилка оновлення бази даних: {e}")

def restart_bot():
    """Перезапускає бота"""
    logger.info("Перезапуск бота...")
    
    # Перевіряємо наявність сценаріїв запуску
    scripts = ['direct_bot_runner.py', 'run_bot.py', 'restart_bot.py']
    script_to_run = None
    
    for script in scripts:
        if os.path.exists(script):
            script_to_run = script
            break
    
    if not script_to_run:
        logger.error("Не знайдено жодного сценарію для запуску бота")
        return False
    
    # Вбиваємо всі процеси Python, які можуть бути ботом
    try:
        if sys.platform == 'win32':
            os.system('taskkill /f /im python.exe /fi "WINDOWTITLE eq bot"')
        else:
            os.system("pkill -f 'python.*bot.*py'")
        
        logger.info("Зупинено попередні процеси бота")
    except Exception as e:
        logger.error(f"Помилка зупинки процесів: {e}")
    
    # Запускаємо бота
    try:
        if sys.platform == 'win32':
            subprocess.Popen(
                [sys.executable, script_to_run],
                creationflags=subprocess.CREATE_NEW_PROCESS_GROUP | subprocess.DETACHED_PROCESS,
                env=os.environ.copy()
            )
        else:
            os.system(f"nohup python {script_to_run} > bot.log 2>&1 &")
        
        logger.info(f"✓ Бот запущено з використанням сценарію {script_to_run}")
        return True
    except Exception as e:
        logger.error(f"Помилка запуску бота: {e}")
        return False

def main():
    """Основна функція для виправлення конфігурації бота"""
    logger.info("=== Початок виправлення конфігурації бота ===")
    
    # Оновлюємо змінні середовища
    os.environ['BOT_TOKEN'] = BOT_TOKEN
    os.environ['BOT_USERNAME'] = BOT_USERNAME
    logger.info("✓ Встановлено змінні середовища")
    
    # Оновлюємо конфігурацію
    update_config_files()
    
    # Оновлюємо базу даних
    update_database()
    
    # Перезапускаємо бота
    restart_success = restart_bot()
    
    if restart_success:
        logger.info("=== Конфігурацію бота успішно виправлено ===")
    else:
        logger.error("=== Помилка перезапуску бота ===")
    
    logger.info("=== Виправлення завершено ===")

if __name__ == "__main__":
    main()
    sys.exit(0) 