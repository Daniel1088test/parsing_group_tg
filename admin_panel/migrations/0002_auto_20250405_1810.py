"""
Міграція для оновлення структури бази даних моделі TelegramSession
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

class Migration(migrations.Migration):
    """
    This is a placeholder migration created to fix a broken dependency.
    It was automatically generated to replace a missing migration.
    """

    dependencies = [
        ('admin_panel', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='telegramsession',
            name='verification_code',
            field=models.CharField(blank=True, max_length=255, null=True),
        ),
        migrations.AddField(
            model_name='telegramsession',
            name='password',
            field=models.CharField(blank=True, max_length=255, null=True),
        ),
        migrations.AddField(
            model_name='telegramsession',
            name='session_data',
            field=models.TextField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='telegramsession',
            name='auth_token',
            field=models.CharField(blank=True, max_length=255, null=True),
        ),
        migrations.AddField(
            model_name='telegramsession',
            name='needs_auth',
            field=models.BooleanField(default=False),
        ),
    ] 