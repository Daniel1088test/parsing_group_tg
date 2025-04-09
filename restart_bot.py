#!/usr/bin/env python3
"""
Скрипт для перезапуску бота з новими налаштуваннями
"""
import os
import sys
import subprocess
import logging
import time
import signal
import json

# Налаштування логування
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Налаштування бота
BOT_TOKEN = "8102516142:AAFTsVXXujHHKoX2KZGqZXBHPBznfgh7kg0"
BOT_USERNAME = "channel_pars_mode_bot"

def find_bot_processes():
    """Знаходить процеси бота, які можливо вже запущені"""
    try:
        import psutil
        bot_processes = []
        
        for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
            try:
                cmdline = proc.info['cmdline']
                if cmdline and any('bot' in cmd.lower() for cmd in cmdline if cmd):
                    if any(x in str(cmdline) for x in ['run_bot.py', 'direct_bot_runner.py', 'tg_bot/bot.py']):
                        bot_processes.append(proc)
                        logger.info(f"Знайдено процес бота: PID {proc.info['pid']}, командa: {' '.join(cmdline)}")
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                pass
        
        return bot_processes
    except ImportError:
        logger.warning("Бібліотека psutil не знайдена. Використовуємо альтернативний метод пошуку процесів.")
        # Альтернативний метод для Windows
        if sys.platform == 'win32':
            try:
                output = subprocess.check_output(['tasklist', '/FI', 'IMAGENAME eq python.exe'], text=True)
                return [line for line in output.split('\n') if 'python' in line.lower()]
            except Exception as e:
                logger.error(f"Помилка пошуку процесів: {e}")
                return []
        # Для Linux/Unix
        else:
            try:
                output = subprocess.check_output(['ps', 'aux'], text=True)
                return [line for line in output.split('\n') if 'python' in line.lower() and 'bot' in line.lower()]
            except Exception as e:
                logger.error(f"Помилка пошуку процесів: {e}")
                return []

def update_bot_settings():
    """Оновлює налаштування бота в усіх конфігураційних файлах"""
    logger.info("Оновлення налаштувань бота в конфігураційних файлах...")
    
    # Оновлюємо .env
    try:
        if os.path.exists('.env'):
            with open('.env', 'r', encoding='utf-8') as f:
                content = f.read()
                
            # Оновлюємо BOT_TOKEN та BOT_USERNAME
            import re
            content = re.sub(r'BOT_TOKEN=.*', f'BOT_TOKEN={BOT_TOKEN}', content)
            content = re.sub(r'BOT_USERNAME=.*', f'BOT_USERNAME={BOT_USERNAME}', content)
            
            with open('.env', 'w', encoding='utf-8') as f:
                f.write(content)
                
            logger.info("✓ Файл .env оновлено")
    except Exception as e:
        logger.error(f"Помилка оновлення .env: {e}")
    
    # Оновлюємо config.py
    try:
        config_path = 'tg_bot/config.py'
        if os.path.exists(config_path):
            with open(config_path, 'r', encoding='utf-8') as f:
                content = f.read()
                
            # Оновлюємо TOKEN_BOT та BOT_USERNAME
            import re
            content = re.sub(
                r'TOKEN_BOT\s*=.*?[\"\'].*?[\"\']', 
                f'TOKEN_BOT = os.environ.get(\'BOT_TOKEN\', "{BOT_TOKEN}")', 
                content
            )
            content = re.sub(
                r'BOT_USERNAME\s*=.*?[\"\'].*?[\"\']', 
                f'BOT_USERNAME = os.environ.get(\'BOT_USERNAME\', "{BOT_USERNAME}")', 
                content
            )
            
            with open(config_path, 'w', encoding='utf-8') as f:
                f.write(content)
                
            logger.info(f"✓ Файл {config_path} оновлено")
    except Exception as e:
        logger.error(f"Помилка оновлення {config_path}: {e}")
    
    # Оновлюємо bot_token.env
    try:
        with open('bot_token.env', 'w', encoding='utf-8') as f:
            f.write(f"BOT_TOKEN={BOT_TOKEN}")
        logger.info("✓ Файл bot_token.env оновлено")
    except Exception as e:
        logger.error(f"Помилка оновлення bot_token.env: {e}")
    
    # Оновлюємо налаштування в базі даних, якщо Django доступний
    try:
        # Ініціалізуємо Django
        os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
        import django
        django.setup()
        
        # Імпортуємо та оновлюємо модель BotSettings
        from admin_panel.models import BotSettings
        
        bot_settings = BotSettings.objects.first()
        if bot_settings:
            bot_settings.bot_token = BOT_TOKEN
            bot_settings.bot_username = BOT_USERNAME
            bot_settings.save()
            logger.info("✓ Налаштування бота оновлено в базі даних")
        else:
            # Створюємо нові налаштування, якщо їх немає
            BotSettings.objects.create(
                bot_token=BOT_TOKEN,
                bot_username=BOT_USERNAME,
                bot_name="Channel Parsing Bot"
            )
            logger.info("✓ Створено нові налаштування бота в базі даних")
    except Exception as e:
        logger.error(f"Помилка оновлення налаштувань у базі даних: {e}")

def stop_bot_processes():
    """Зупиняє всі процеси бота"""
    logger.info("Зупинка процесів бота...")
    
    processes = find_bot_processes()
    if not processes:
        logger.info("Активних процесів бота не знайдено")
        return
    
    for proc in processes:
        try:
            if hasattr(proc, 'terminate'):
                proc.terminate()
                logger.info(f"Процес PID {proc.pid} зупинено")
            else:
                # Якщо це просто рядок з інформацією процесу (для альтернативного методу)
                if isinstance(proc, str):
                    parts = proc.split()
                    if len(parts) > 1:
                        pid = parts[1]
                        try:
                            os.kill(int(pid), signal.SIGTERM)
                            logger.info(f"Процес PID {pid} зупинено")
                        except:
                            pass
        except Exception as e:
            logger.error(f"Помилка зупинки процесу: {e}")
    
    # Даємо процесам час на зупинку
    time.sleep(2)

def start_bot():
    """Запускає бота"""
    logger.info("Запуск бота...")
    
    # Перевіряємо наявність різних скриптів для запуску
    if os.path.exists('direct_bot_runner.py'):
        script = 'direct_bot_runner.py'
    elif os.path.exists('run_bot.py'):
        script = 'run_bot.py'
    elif os.path.exists('tg_bot/bot.py'):
        script = 'tg_bot/bot.py'
    else:
        logger.error("Не знайдено жодного скрипта для запуску бота")
        return False
    
    try:
        # Запускаємо бота у фоновому режимі
        if sys.platform == 'win32':
            # Для Windows використовуємо CREATE_NEW_PROCESS_GROUP та DETACHED_PROCESS
            import subprocess
            subprocess.Popen(
                [sys.executable, script],
                creationflags=subprocess.CREATE_NEW_PROCESS_GROUP | subprocess.DETACHED_PROCESS,
                env=os.environ.copy()
            )
        else:
            # Для Unix використовуємо nohup
            os.system(f"nohup python {script} > bot.log 2>&1 &")
        
        logger.info(f"✅ Бот успішно запущено з використанням скрипта {script}")
        return True
    except Exception as e:
        logger.error(f"Помилка запуску бота: {e}")
        return False

def main():
    """Основна функція перезапуску бота"""
    logger.info("=== Початок перезапуску бота ===")
    
    # Оновлюємо налаштування
    update_bot_settings()
    
    # Зупиняємо всі процеси бота
    stop_bot_processes()
    
    # Запускаємо бота
    success = start_bot()
    
    if success:
        logger.info("=== Бот успішно перезапущено ===")
    else:
        logger.error("=== Помилка перезапуску бота ===")

if __name__ == "__main__":
    main()
    sys.exit(0) 