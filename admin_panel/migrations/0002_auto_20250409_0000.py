from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ('admin_panel', '0001_initial'),
    ]

    operations = [
        migrations.AlterField(
            model_name='message',
            name='telegram_channel_id',
            field=models.CharField(blank=True, max_length=255, null=True),
        ),
        migrations.AlterField(
            model_name='message',
            name='media',
            field=models.FileField(blank=True, null=True, upload_to='messages'),
        ),
        migrations.AlterField(
            model_name='message',
            name='media_type',
            field=models.CharField(blank=True, choices=[('text', 'Text Only'), ('photo', 'Photo'), ('video', 'Video'), ('document', 'Document'), ('audio', 'Audio'), ('voice', 'Voice'), ('sticker', 'Sticker'), ('gif', 'GIF'), ('webpage', 'Web Page'), ('webpage_photo', 'Web Page with Photo')], default='text', max_length=50, null=True),
        ),
        migrations.AlterField(
            model_name='telegramsession',
            name='session_file',
            field=models.CharField(blank=True, max_length=255, null=True),
        ),
        migrations.AlterField(
            model_name='telegramsession',
            name='phone',
            field=models.CharField(max_length=20, unique=True),
        ),
        migrations.AddField(
            model_name='telegramsession',
            name='needs_auth',
            field=models.BooleanField(default=True, help_text='Indicates if this session needs to be authenticated'),
        ),
    ] 