#!/usr/bin/env python3
"""
Простий скрипт для налаштування токену Telegram бота.
Запустіть цей скрипт, щоб швидко встановити токен у всіх необхідних місцях.
"""

import os
import sys

def clear_screen():
    """Очищення екрану консолі."""
    os.system('cls' if os.name == 'nt' else 'clear')

def print_header():
    """Виводить заголовок."""
    clear_screen()
    print("=" * 50)
    print("         НАЛАШТУВАННЯ ТОКЕНУ TELEGRAM БОТА")
    print("=" * 50)
    print("\nЦей скрипт допоможе налаштувати токен вашого Telegram бота.\n")

def get_token_from_user():
    """Запитує токен у користувача."""
    print("Вам потрібно отримати токен від @BotFather у Telegram.")
    print("Інструкція:")
    print("1. Відкрийте Telegram")
    print("2. Знайдіть @BotFather")
    print("3. Відправте /newbot або використайте існуючого бота")
    print("4. Скопіюйте токен, який виглядає як: 123456789:ABCDefGhIJKlmNoPQRsTUVwxyZ")
    print("\n")
    
    token = input("Введіть токен вашого бота: ").strip()
    
    # Перевірка формату токену
    if ":" not in token or len(token) < 20:
        print("\n⚠️ УВАГА: Введений токен не схожий на правильний формат Telegram бота.")
        confirm = input("Все одно використовувати цей токен? (так/ні): ").strip().lower()
        if confirm != "так":
            return None
    
    return token

def save_token(token):
    """Зберігає токен у різних місцях."""
    # 1. Зберігаємо в config.py
    try:
        config_path = os.path.join('tg_bot', 'config.py')
        if os.path.exists(config_path):
            with open(config_path, 'r', encoding='utf-8') as f:
                lines = f.readlines()
            
            with open(config_path, 'w', encoding='utf-8') as f:
                for line in lines:
                    if line.startswith('TOKEN_BOT'):
                        f.write(f'TOKEN_BOT = os.environ.get(\'BOT_TOKEN\', "{token}")\n')
                    else:
                        f.write(line)
            print("✅ Токен оновлено в tg_bot/config.py")
        else:
            print(f"❌ Файл {config_path} не знайдено")
    except Exception as e:
        print(f"❌ Помилка оновлення config.py: {e}")
    
    # 2. Зберігаємо в .env файл
    try:
        with open('.env', 'a+', encoding='utf-8') as f:
            f.seek(0)
            content = f.read()
            if 'BOT_TOKEN' in content:
                # Оновлюємо існуючий токен
                lines = content.split('\n')
                with open('.env', 'w', encoding='utf-8') as f_write:
                    for line in lines:
                        if line.startswith('BOT_TOKEN='):
                            f_write.write(f'BOT_TOKEN={token}\n')
                        else:
                            f_write.write(f'{line}\n')
            else:
                # Додаємо новий токен
                f.write(f'\nBOT_TOKEN={token}\n')
        print("✅ Токен оновлено в .env файлі")
    except Exception as e:
        print(f"❌ Помилка оновлення .env файлу: {e}")
    
    # 3. Зберігаємо в bot_token.env для Railway
    try:
        with open('bot_token.env', 'w', encoding='utf-8') as f:
            f.write(f"BOT_TOKEN={token}")
        print("✅ Токен оновлено в bot_token.env")
    except Exception as e:
        print(f"❌ Помилка оновлення bot_token.env: {e}")
    
    # 4. Встановлюємо змінну середовища
    os.environ['BOT_TOKEN'] = token
    print("✅ Токен встановлено як змінну середовища")
    
    # 5. Оновлюємо в базі даних, якщо Django доступний
    try:
        # Ініціалізуємо Django
        os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
        import django
        django.setup()
        
        # Імпортуємо та оновлюємо модель BotSettings
        from admin_panel.models import BotSettings
        bot_settings, created = BotSettings.objects.get_or_create(pk=1)
        bot_settings.bot_token = token
        bot_settings.save()
        print("✅ Токен оновлено в базі даних")
    except Exception as e:
        print(f"❌ Помилка оновлення в базі даних: {e}")

def verify_token(token):
    """Перевіряє валідність токену."""
    try:
        import asyncio
        from aiogram import Bot
        
        async def check_token():
            try:
                bot = Bot(token=token)
                me = await bot.get_me()
                await bot.session.close()
                return True, me.username
            except Exception as e:
                return False, str(e)
        
        # Запускаємо асинхронну перевірку
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            valid, result = loop.run_until_complete(check_token())
            return valid, result
        finally:
            loop.close()
    except Exception as e:
        return False, str(e)

def main():
    print_header()
    
    # Отримуємо токен від користувача
    token = get_token_from_user()
    if not token:
        print("\n❌ Налаштування токену скасовано.")
        return False
    
    # Перевіряємо токен
    print("\nПеревірка токену...")
    valid, result = verify_token(token)
    
    if valid:
        print(f"\n✅ Токен дійсний! З'єднано з ботом @{result}")
        
        # Зберігаємо токен
        print("\nЗберігаємо токен у різних місцях...")
        save_token(token)
        
        print("\n" + "=" * 50)
        print("✅ ТОКЕН УСПІШНО НАЛАШТОВАНО!")
        print("=" * 50)
        print("\nЩоб запустити бота:")
        print("1. Перезапустіть програму: python run.py")
        print("2. Або перезапустіть деплоймент на Railway")
        
        return True
    else:
        print(f"\n❌ Токен недійсний: {result}")
        retry = input("\nВсе одно зберегти цей токен? (так/ні): ").strip().lower()
        if retry == "так":
            print("\nЗберігаємо токен, незважаючи на помилку перевірки...")
            save_token(token)
            print("\n⚠️ Токен збережено, але він може не працювати.")
            return True
        else:
            print("\n❌ Налаштування токену скасовано.")
            return False

if __name__ == "__main__":
    try:
        success = main()
        if not success:
            print("\nДля отримання допомоги щодо створення бота в Telegram:")
            print("1. Відкрийте Telegram і знайдіть @BotFather")
            print("2. Відправте команду /start, потім /newbot")
            print("3. Дотримуйтесь інструкцій для створення нового бота")
            print("\nПісля отримання токену запустіть цей скрипт знову.")
    except KeyboardInterrupt:
        print("\n\nНалаштування скасовано користувачем.")
    except Exception as e:
        print(f"\n\nСталася непередбачена помилка: {e}")
    
    input("\nНатисніть Enter для виходу...")
    sys.exit(0) 