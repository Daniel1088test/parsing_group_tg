# Railway Deployment Guide

## Step 1: Prepare Your Project

Your project is already configured for Railway deployment with the following files:
- `railway.json` - Configuration for Railway
- `start.sh` - Script to start the application
- `migrate.sh` - Script to run database migrations

## Step 2: Set Up Your Railway Project

1. Create an account on [Railway](https://railway.app/) if you don't have one
2. Create a new project in Railway
3. Add a PostgreSQL database to your project:
   - Click on "New" → "Database" → "PostgreSQL"
   - Wait for the database to be provisioned

## Step 3: Set Environment Variables

**IMPORTANT**: You must set these environment variables in Railway dashboard:

1. Go to your project settings
2. Go to the "Variables" tab
3. Add the following environment variables:

```
DATABASE_URL=postgresql://postgres:urCNhXdwvbqOvvEsJDffIiDUMcLhAvcs@switchback.proxy.rlwy.net:10052/railway
DEBUG=False
SECRET_KEY=your-secure-secret-key
ALLOWED_HOSTS=.railway.app,your-app-name.up.railway.app
BOT_TOKEN=your_telegram_bot_token
API_ID=your_telegram_api_id
API_HASH=your_telegram_api_hash
```

Replace the values with your actual values.

## Step 4: Deploy Your Service

1. Connect your GitHub repository to Railway
   - Click on "New" → "GitHub Repo"
   - Select your repository
   
2. Configure the service:
   - Railway should automatically detect your `railway.json` configuration
   - If not, make sure to set:
     - Build command: `pip install -r requirements.txt`
     - Start command: `bash start.sh`

3. Deploy your service
   - Click "Deploy" and wait for the build to complete

## Step 5: Verify Deployment

1. Check the logs in Railway dashboard
2. Confirm that migrations ran successfully
3. Access your application at the URL provided by Railway

## Troubleshooting

If you encounter errors:

1. **Database Connection Issues**:
   - Check if `DATABASE_URL` is correctly set in Railway variables
   - Make sure the PostgreSQL service is running properly
   - Verify connection string format and credentials

2. **Migration Errors**:
   - Check logs for specific migration errors
   - You can run migrations manually by accessing the Railway shell:
     ```
     railway shell
     python manage.py migrate
     ```

3. **Application Not Starting**:
   - Check for errors in the application logs
   - Verify all required environment variables are set
   - Ensure the PostgreSQL connection is working

## Connecting to Your Database Manually

You can connect to your PostgreSQL database using these commands:

```bash
# Using Railway CLI
railway connect Postgres

# Using psql command-line
PGPASSWORD=urCNhXdwvbqOvvEsJDffIiDUMcLhAvcs psql -h switchback.proxy.rlwy.net -U postgres -p 10052 -d railway
``` 