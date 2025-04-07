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
   
6. Deploy the application
7. Once deployed, Railway will automatically run the commands from the Procfile:
   - `web: python run.py` - Web server process
   - `worker: python run.py` - Background worker process

## Important Notes

- The first time you deploy, you'll need to authorize Telethon for your Telegram user account
- The migration script will automatically run when deploying to Railway
- Monitor your app logs in Railway dashboard for any issues
- Update `SECRET_KEY` to a secure value

## Database Setup

Railway automatically provisions a PostgreSQL database. It's configured automatically with this connection string:

```
postgresql://postgres:urCNhXdwvbqOvvEsJDffIiDUMcLhAvcs@switchback.proxy.rlwy.net:10052/railway
```

The database connection is preconfigured in the `.env` file. If you need to connect to the database manually, you can use:

- **Host**: switchback.proxy.rlwy.net
- **Port**: 10052
- **Database**: railway
- **Username**: postgres
- **Password**: urCNhXdwvbqOvvEsJDffIiDUMcLhAvcs

You can also access the database via Railway CLI with:

```
railway connect Postgres
```

## Connecting to the database

There are multiple ways to connect to your PostgreSQL database:

1. **Using pgAdmin:**
   - Add a new server
   - Fill in the connection details from above
   - Connect and manage your database

2. **Using psql command-line:**
   ```
   PGPASSWORD=urCNhXdwvbqOvvEsJDffIiDUMcLhAvcs psql -h switchback.proxy.rlwy.net -U postgres -p 10052 -d railway
   ```

3. **Using the test_db_connection.py script:**
   ```
   python test_db_connection.py
   ```

## Migrations

Migrations will run automatically on deployment, but you can also run them manually:

```
python manage.py migrate
```

## Creating a superuser

To create a Django admin superuser:

```
python manage.py createsuperuser
```

## Scaling

Railway allows you to scale your application as needed through their dashboard. 