from django.db import migrations, models
from django.utils import timezone

def set_created_at_default(apps, schema_editor):
    """Set default value for created_at field on existing rows with NULL values"""
    TelegramSession = apps.get_model('admin_panel', 'TelegramSession')
    for session in TelegramSession.objects.filter(created_at__isnull=True):
        session.created_at = timezone.now()
        session.save()

class Migration(migrations.Migration):

    dependencies = [
        ('admin_panel', '0005_remove_telegramsession_needs_auth'),
    ]

    operations = [
        # First make the field nullable temporarily
        migrations.AlterField(
            model_name='telegramsession',
            name='created_at',
            field=models.DateTimeField(null=True, blank=True),
        ),
        
        # Run the data migration to fix null values
        migrations.RunPython(set_created_at_default),
        
        # Set back to non-nullable with auto_now_add
        migrations.AlterField(
            model_name='telegramsession',
            name='created_at',
            field=models.DateTimeField(auto_now_add=True),
        ),
    ]