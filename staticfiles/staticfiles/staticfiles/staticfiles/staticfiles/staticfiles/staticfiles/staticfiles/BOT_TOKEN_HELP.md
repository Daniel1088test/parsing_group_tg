# Fixing Telegram Bot Token Issues

This document explains how to fix issues with your Telegram bot token.

## The Problem

Your bot is failing to start with the error:
```
Bot token verification failed: Telegram server says - Unauthorized
```

This means the bot token is invalid, expired, or revoked.

## Solution

You need to set a valid Telegram bot token. Follow these steps:

### Option 1: Use the fix_token.py Script (Recommended)

1. Run the script:
   ```
   python fix_token.py
   ```

2. When prompted, enter your valid Telegram bot token.

3. The script will verify the token, save it to all necessary locations, and restart the bot.

### Option 2: Manual Configuration

If you prefer to set the token manually:

1. Get a valid bot token from @BotFather on Telegram

2. Update one of these locations:
   - Edit `tg_bot/config.py` and set `TOKEN_BOT = "your_token_here"`
   - Set environment variable: `export BOT_TOKEN=your_token_here`
   - Update the token in your Django admin panel (BotSettings)

3. Restart your application or Railway deployment

## Getting a New Bot Token

If you need to create a new bot or regenerate the token:

1. Open Telegram and message [@BotFather](https://t.me/BotFather)
2. Use `/newbot` to create a new bot, or `/revoke` to regenerate a token
3. BotFather will give you a token like `123456789:ABCDefGhIJKlmNoPQRsTUVwxyZ`
4. Use this token in the steps above

## Testing Bot Connectivity

After setting the token, you can test if your bot is working by:

1. Running `python set_bot_token.py` which will validate the token
2. Sending a `/start` command to your bot on Telegram
3. Checking the logs for successful connection messages

## Need Help?

If you continue experiencing issues, please:
1. Check the application logs for detailed error messages
2. Ensure your Telegram bot is not disabled
3. Verify that your internet connection allows access to Telegram API

For more help with Telegram bots, visit: https://core.telegram.org/bots 