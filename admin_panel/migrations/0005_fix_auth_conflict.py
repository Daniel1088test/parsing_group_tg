from django.db import migrations, models


class Migration(migrations.Migration):
    """
    Migration to fix conflicts with authentication fields by properly
    redefining them after the merge migration.
    """

    dependencies = [
        ('admin_panel', '0004_merge_20250408_1830'),
    ]

    operations = [
        # Re-add the fields from conflicting migrations
        migrations.AddField(
            model_name='telegramsession',
            name='verification_code',
            field=models.CharField(blank=True, help_text='Verification code for authentication', max_length=10, null=True),
        ),
        migrations.AddField(
            model_name='telegramsession',
            name='password',
            field=models.CharField(blank=True, help_text='Password for 2FA if required', max_length=50, null=True),
        ),
        migrations.AddField(
            model_name='telegramsession',
            name='session_data',
            field=models.TextField(blank=True, help_text='Encoded session data for persistent storage', null=True),
        ),
        migrations.AlterField(
            model_name='telegramsession',
            name='auth_token',
            field=models.CharField(blank=True, help_text='Token for authorizing this session via bot', max_length=255, null=True),
        ),
        migrations.AlterField(
            model_name='telegramsession',
            name='needs_auth',
            field=models.BooleanField(default=True, help_text='Indicates if this session needs manual authentication'),
        ),
    ] 