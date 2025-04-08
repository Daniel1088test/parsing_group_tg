# Generated manually

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("admin_panel", "0010_telegramsession_session_data"),
    ]

    operations = [
        migrations.AddField(
            model_name="telegramsession",
            name="session_data",
            field=models.TextField(
                blank=True,
                help_text="Encoded session data for persistent storage",
                null=True,
            ),
        ),
        migrations.AddField(
            model_name="telegramsession",
            name="needs_auth",
            field=models.BooleanField(
                default=True,
                help_text="Indicates if this session needs manual authentication"
            ),
        ),
        migrations.AddField(
            model_name="telegramsession",
            name="auth_token",
            field=models.CharField(
                blank=True,
                help_text="Token for authorizing this session via bot",
                max_length=255,
                null=True,
            ),
        ),
    ] 