from django.db import migrations
from django.utils import timezone

def set_created_at_default(apps, schema_editor):
    # Використовуємо безпечний підхід з обробкою помилок
    TelegramSession = apps.get_model('admin_panel', 'TelegramSession')
    
    try:
        # Отримуємо лише поля, які гарантовано існують
        for session in TelegramSession.objects.filter(created_at__isnull=True).only('id', 'created_at'):
            session.created_at = timezone.now()
            session.save(update_fields=['created_at'])
    except Exception as e:
        # Запис помилки та продовження виконання міграції
        print(f"Error updating created_at: {e}")
        # Використовуємо прямий SQL запит як запасний варіант
        db_alias = schema_editor.connection.alias
        schema_editor.execute(
            f"UPDATE admin_panel_telegramsession SET created_at = '{timezone.now().isoformat()}' WHERE created_at IS NULL",
            params=None
        )

class Migration(migrations.Migration):

    dependencies = [
        ('admin_panel', '0001_initial'),
    ]

    operations = [
        migrations.RunPython(set_created_at_default, migrations.RunPython.noop),
    ]