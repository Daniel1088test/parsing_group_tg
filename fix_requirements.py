#!/usr/bin/env python3
"""
Скрипт для виправлення конфліктів у файлі requirements.txt при розгортанні на Railway
"""
import re
import sys
import os
import logging

# Конфігурація логування
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger('fix_requirements')

# Список проблемних залежностей та їх виправлення
FIXES = {
    r'aiofiles==24\.1\.0': 'aiofiles~=23.2.1',  # Фіксуємо конфлікт з aiogram
    r'daphne==4\.0\.0': 'daphne==3.0.2',        # Знижуємо версію daphne
    r'channels==4\.0\.0': 'channels==3.0.5',    # Знижуємо версію channels
    r'channels-redis==4\.1\.0': 'channels-redis==4.0.0',  # Знижуємо версію channels-redis
    r'gevent==23\.9\.1': 'gevent==22.10.2',     # Встановлюємо стабільнішу версію gevent
    r'pyaes==1\.6\.1': 'pyaes==1.6.1',          # Ensure specific version for pyaes
    r'aiohttp==3\.11\.14': 'aiohttp~=3.9.0',    # Downgrade aiohttp to be compatible with aiogram 3.2.0
}

# Additional packages to add if they don't exist in requirements
ADDITIONAL_PACKAGES = [
    'wheel==0.43.0',  # Ensure wheel is explicitly installed for building packages
    'setuptools>=65.5.1',  # Ensure setuptools is up to date
]

def fix_requirements_file(file_path):
    """Виправляє конфлікти у файлі requirements.txt"""
    try:
        if not os.path.exists(file_path):
            logger.error(f"Файл {file_path} не знайдено")
            return False
        
        # Читаємо файл
        logger.info(f"Читаємо файл {file_path}")
        with open(file_path, 'r') as file:
            content = file.read()
        
        # Створюємо резервну копію
        backup_path = f"{file_path}.bak"
        with open(backup_path, 'w') as backup:
            backup.write(content)
        logger.info(f"Створено резервну копію у {backup_path}")
        
        # Виправляємо конфлікти
        fixed_content = content
        for pattern, replacement in FIXES.items():
            old_content = fixed_content
            fixed_content = re.sub(pattern, replacement, fixed_content)
            if old_content != fixed_content:
                logger.info(f"Виправлено: {pattern} -> {replacement}")
        
        # Check if we need to add additional packages
        lines = fixed_content.splitlines()
        for package in ADDITIONAL_PACKAGES:
            package_name = package.split('==')[0].split('>=')[0].strip()
            if not any(line.strip().startswith(package_name) for line in lines):
                logger.info(f"Додаємо пакет: {package}")
                lines.append(package)
                
        fixed_content = '\n'.join(lines)
        
        # Записуємо виправлений файл
        if content != fixed_content:
            with open(file_path, 'w') as file:
                file.write(fixed_content)
            logger.info(f"Файл {file_path} успішно оновлено")
            return True
        else:
            logger.info(f"Файл {file_path} не потребує змін")
            return True
    
    except Exception as e:
        logger.error(f"Помилка при виправленні файлу {file_path}: {e}")
        return False

def main():
    # Шлях до файлу requirements.txt
    requirements_path = 'requirements.txt'
    
    # Перевіряємо аргументи командного рядка
    if len(sys.argv) > 1:
        requirements_path = sys.argv[1]
    
    logger.info(f"=== Починаємо виправлення файлу {requirements_path} ===")
    result = fix_requirements_file(requirements_path)
    
    if result:
        logger.info("=== Виправлення успішно завершено ===")
        return 0
    else:
        logger.error("=== Виправлення завершилося з помилками ===")
        return 1

if __name__ == "__main__":
    sys.exit(main()) 