# Telegram Parser App

A Django application for parsing and monitoring Telegram channels.

## Deployment on Railway

### Quick Deploy

1. Click the button below to deploy this application to Railway:

[![Deploy on Railway](https://railway.app/button.svg)](https://railway.app/template/...)

2. Set up required environment variables in Railway dashboard:
   - `BOT_TOKEN` - Telegram Bot API token
   - `DJANGO_SECRET_KEY` - Secret key for Django
   - `DATABASE_URL` - Will be set automatically if you add a PostgreSQL database

### Manual Deployment

1. Create a new project in Railway
2. Add a PostgreSQL database
3. Connect your GitHub repository
4. Configure environment variables:
   - `BOT_TOKEN` - Telegram Bot API token
   - `DJANGO_SECRET_KEY` - Secret key for Django
5. Deploy the application

## Fixing Common Deployment Issues

### Static Files Issues

If you encounter issues with static files deployment, run:

```bash
python fix_static_files.py
```

This will:
1. Clean up nested staticfiles directories
2. Fix the STATICFILES_DIRS setting
3. Ensure STATIC_ROOT is correctly configured

### Whitenoise Issues

If you see errors related to missing CSS files with paths like `staticfiles/staticfiles/staticfiles/...`, run:

```bash
python fix_whitenoise.py
```

This will switch the static files storage to a simpler whitenoise storage class that doesn't use file manifests.

### Missing Dependencies

If you see errors related to missing Python modules, ensure all dependencies are in requirements.txt:

```bash
python -m pip install -r requirements.txt
```

### Local Development

To run the application locally:

```bash
# Install dependencies
pip install -r requirements.txt

# Apply migrations
python manage.py migrate

# Collect static files
python manage.py collectstatic --noinput

# Start the server
python manage.py runserver
```

## Features

- Monitor Telegram channels
- Parse messages from channels
- Categorize channels
- Manage multiple Telegram sessions
- Easy web interface for management

## License

This project is licensed under the MIT License - see the LICENSE file for details. 