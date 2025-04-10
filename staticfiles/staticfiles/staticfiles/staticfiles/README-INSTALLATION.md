# Telegram Parser System - Installation Guide

This guide provides instructions for installing and running the Telegram Parser system, which includes a Django web interface, a Telegram bot for channel monitoring, and database components.

## System Requirements

- Python 3.8 or higher
- PostgreSQL (for Railway deployment) or SQLite (for local development)
- Internet connection for Telegram API access

## Installation

### Local Development Setup

1. Clone the repository or extract the files to your desired location.

2. Install the required dependencies:
   ```
   pip install -r requirements.txt
   ```

3. Create a `.env` file in the project root with the following content:
   ```
   BOT_TOKEN=your_telegram_bot_token
   BOT_USERNAME=your_bot_username
   DEBUG=True
   ```

4. Run the database migration and fixes:
   ```
   python fix_templates_and_aiohttp.py
   python fix_multiple_fields.py
   python fix_admin_query.py
   ```

5. Start the application:
   ```
   python run_all.py
   ```

   This will start both the Django web interface and the Telegram bot.

6. Access the web interface at `http://localhost:8000/`

### Railway Deployment

1. Create a new project on Railway.

2. Link your GitHub repository to the Railway project.

3. Configure the following environment variables in Railway:
   - `BOT_TOKEN` - Your Telegram bot token
   - `BOT_USERNAME` - Your Telegram bot username
   - `DEBUG` - Set to `False` for production
   - `SECRET_KEY` - A secure random string for Django

4. Railway will automatically detect the PostgreSQL requirements and set up a database.

5. The application will automatically run the fix scripts during startup.

## Running the Application

### Using the All-In-One Script

The easiest way to run the entire application is with the `run_all.py` script:

```
python run_all.py
```

This script:
- Runs all necessary database fixes
- Starts the Django web server
- Starts the Telegram bot
- Monitors both processes and restarts them if they fail

### Running Components Separately

If you need to run components separately:

1. Run the Django web server:
   ```
   python manage.py runserver 0.0.0.0:8000
   ```

2. Run the Telegram bot:
   ```
   python run_bot.py
   ```

## Troubleshooting

### Database Issues

If you encounter database issues (missing fields or broken relationships):

1. Run the fix scripts in sequence:
   ```
   python fix_templates_and_aiohttp.py
   python fix_multiple_fields.py
   python fix_admin_query.py
   ```

### Railway Deployment Issues

If the application isn't working properly on Railway:

1. Check the Railway logs for errors.

2. Run the following command to fix Railway-specific issues:
   ```
   python fix_railway_deployment.py
   ```

3. Make sure all required environment variables are set in Railway.

### Authorization Issues

If Telegram session authorization isn't working:

1. Run the fix script:
   ```
   python fix_session_auth.py
   ```

2. Try re-authorizing the session through the web interface.

## Additional Help

For more detailed instructions, refer to:
- `BOT_TOKEN_HELP.md` - For help with setting up your Telegram bot token
- `RAILWAY-BOT-SETUP.md` - For detailed Railway deployment instructions
- `BOT_FIXES.md` - For common fixes to bot issues

## License

This project is proprietary. All rights reserved. 