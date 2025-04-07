# Railway Deployment Guide

## Prerequisites
- A Railway account (https://railway.app)
- Your code pushed to a Git repository
- Telegram Bot token (from @BotFather)
- Telegram API credentials (from https://my.telegram.org/apps)

## Deployment Steps

1. Fork or clone this repository to your GitHub account
2. Log in to Railway and create a new project
3. Select "Deploy from GitHub repo"
4. Connect your GitHub account and select this repository
5. Add the required environment variables in Railway dashboard:
   - Copy variables from `.env.example` and set appropriate values
   - Make sure to set `DEBUG=False` for production
   - Set `ALLOWED_HOSTS` to include your Railway app domain
   - Set `DATABASE_URL` (or Railway will provide this automatically)
   
6. Deploy the application
7. Once deployed, Railway will automatically run the commands from the Procfile:
   - `web: python run.py` - Web server process
   - `worker: python run.py` - Background worker process

## Important Notes

- The first time you deploy, you'll need to authorize Telethon for your Telegram user account
- Make sure your database migrations are applied before starting the app
- Monitor your app logs in Railway dashboard for any issues
- Update `SECRET_KEY` to a secure value

## Database Setup

Railway automatically provisions a PostgreSQL database. To initialize it:

1. Go to your project in Railway dashboard
2. Open a shell for your deployed application
3. Run the following commands:
```
python manage.py migrate
python manage.py createsuperuser
```

## Scaling

Railway allows you to scale your application as needed through their dashboard. 