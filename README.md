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

**Important**: Before the parser can work correctly, you must authorize a Telegram user account. The error "The key is not registered in the system" indicates that your session is not authorized.

### Authorization Methods

#### Method 1: Using the Authorization Helper (Recommended)

Run the following command:

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
The authorization will run on the server console, so you'll need to check the terminal where the bot is running.

### Troubleshooting

If you're seeing errors like "The key is not registered in the system" or "Session exists but is not authorized", you need to properly authorize a Telegram user account for the parser to work.

Common issues:

1. **Using a bot account instead of a user account**: You must use a regular Telegram user account, not a bot.
2. **Authentication expired**: Telegram sessions can expire; reauthorize using one of the methods above.
3. **Rate limiting**: If you see "FloodWaitError", you've been rate limited. Wait the specified time before trying again.

## Commands

- `/start`: Start the bot
- `/forceparse <channel_link>`: Test parsing for a specific channel
- `/authorize_telethon`: Start the Telethon authorization process
- `/ping`: Check if the bot is running
