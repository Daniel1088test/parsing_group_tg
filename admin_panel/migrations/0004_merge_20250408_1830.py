from django.db import migrations


class Migration(migrations.Migration):
    """
    This is a merge migration to resolve conflicting migrations:
    - 0001_message_original_url
    - 0002_auto_20250405_1810
    - 0003_add_telegram_session_fields
    """

    dependencies = [
        ('admin_panel', '0001_message_original_url'),
        ('admin_panel', '0002_auto_20250405_1810'),
        ('admin_panel', '0003_add_telegram_session_fields'),
    ]

    operations = [
        # No operations needed - this migration just serves to merge the branches
    ] 