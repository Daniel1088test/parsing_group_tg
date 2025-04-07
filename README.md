# Group-parser-with-admin
Telethon + Django

# Telegram Channel Parser

This application allows you to parse messages from Telegram channels and store them in a database.

## Setup

1. Clone the repository
2. Install the dependencies: `pip install -r requirements.txt`
3. Configure your environment variables (see `.env.example`)
4. Run the application: `python -m tg_bot.bot`

## Telethon Authorization

**IMPORTANT**: The parser needs a properly authorized Telegram user account to work. The error "The key is not registered in the system" indicates your session is not authorized.

### Fixing the Parsing Issue for Railway Deployment

The main issue with Railway deployment is that it cannot handle interactive authentication prompts. You must create an authorized session file locally and upload it to Railway.

#### Step 1: Create an Authorized Session

Run this command on your local machine:

```bash
python create_session_for_railway.py
```

This interactive script will:
1. Guide you through Telegram authorization
2. Create a `telethon_session.session` file
3. Make copies with alternative names for compatibility

#### Step 2: Upload the Session File to Railway

Once the session file is created:
1. Upload the `telethon_session.session` file to your Railway project
2. Redeploy your application

#### Step 3: Verify the Parser

After redeploying, the parser should now work correctly. You can verify this by:
1. Checking the logs for successful connection messages
2. Using the `/forceparse` command in the bot to test parsing a specific channel

### Alternative Authorization Methods

#### Method 1: Using the Authorization Helper

Run the following command locally:

```bash
python authorize_telegram.py
```

This will guide you through the authorization process with a user-friendly interface.

#### Method 2: Using the Command Line

Run the Telethon authorization directly:

```bash
python -m tg_bot.auth_telethon --force
```

Options:
- `--force`: Force reauthorization even if a session exists
- `--delete`: Delete any existing session and create a new one

#### Method 3: Via the Bot (Admin Only)

If you're an admin, you can use the `/authorize_telethon` command in the bot chat.
**Note**: This only works in local development, not on Railway.

### Troubleshooting

If parsing is still not working:

1. **Check the logs**: Look for errors related to Telethon or session authorization
2. **Verify session file**: Make sure the session file is named correctly and uploaded to Railway
3. **Check API credentials**: Ensure your API_ID and API_HASH are correct in the code and environment variables
4. **Session expired**: Telegram sessions can expire; create a new one if this happens
5. **Try a fresh session**: Delete existing session files and create a new one

## Commands

- `/start`: Start the bot
- `/forceparse <channel_link>`: Test parsing for a specific channel
- `/authorize_telethon`: Start the Telethon authorization process (local only)
- `/ping`: Check if the bot is running

## Production Deployment Notes

When deploying to Railway or other cloud platforms:

1. Always use pre-authorized session files
2. Never rely on interactive authentication methods
3. Make sure to handle EOFError and other exceptions that might occur in non-interactive environments
4. Consider using the `cryptg` module for better encryption performance
