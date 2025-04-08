"""
Додаткова міграція для полів, яких може не вистачати в TelegramSession
"""
from django.db import migrations, models

def check_column_exists(apps, schema_editor, table_name, column_name):
    """Перевіряє наявність колонки в таблиці"""
    db_alias = schema_editor.connection.alias
    cursor = schema_editor.connection.cursor()
    
    # SQLite специфічна команда для перевірки
    cursor.execute(
        f"PRAGMA table_info({table_name});"
    )
    columns = [column[1] for column in cursor.fetchall()]
    return column_name in columns

def add_fields_conditionally(apps, schema_editor):
    """Додає поля тільки якщо вони не існують"""
    db_alias = schema_editor.connection.alias
    
    # Перевіряємо, чи існує таблиця
    try:
        cursor = schema_editor.connection.cursor()
        cursor.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='admin_panel_telegramsession';"
        )
        if not cursor.fetchone():
            return  # Таблиця не існує
            
        # Поля, які слід перевірити
        fields_to_check = [
            'session_name', 'session_string', 'is_bot'
        ]
        
        for field in fields_to_check:
            if not check_column_exists(apps, schema_editor, 'admin_panel_telegramsession', field):
                # Додаємо поле, якщо воно не існує
                if field == 'session_name':
                    cursor.execute(
                        "ALTER TABLE admin_panel_telegramsession ADD COLUMN session_name VARCHAR(255) DEFAULT 'default';"
                    )
                elif field == 'session_string':
                    cursor.execute(
                        "ALTER TABLE admin_panel_telegramsession ADD COLUMN session_string TEXT NULL;"
                    )
                elif field == 'is_bot':
                    cursor.execute(
                        "ALTER TABLE admin_panel_telegramsession ADD COLUMN is_bot BOOLEAN DEFAULT 0;"
                    )
    except Exception as e:
        print(f"Помилка при перевірці полів: {e}")

class Migration(migrations.Migration):

    dependencies = [
        ('admin_panel', '0002_auto_20250405_1810'),
    ]

    operations = [
        migrations.RunPython(add_fields_conditionally),
    ] 