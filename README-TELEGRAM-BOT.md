# Telegram Channel Parser Bot

This bot allows you to monitor and parse messages from Telegram channels.

## Features

- Authorize Telegram sessions to parse private channels
- View the latest messages from channels
- Categorize channels for better organization
- Access parsed messages through the web interface

## Setup and Running

### Quick Start

The easiest way to run the bot is using the `start_bot.py` script:

```bash
python start_bot.py
```

This script will:
1. Kill any existing Python processes
2. Fix database configuration
3. Fix migration files if needed
4. Apply database migrations
5. Start the bot in the background

You can then access the bot at https://t.me/chan_parsing_mon_bot

### Alternate Startup Methods

If you encounter issues with the quick start, you can try these alternatives:

1. Direct bot script:
```bash
python tg_bot/bot.py
```

2. Run with fixes:
```bash
python fix_bot_integration.py && python tg_bot/bot.py
```

3. Full fix and run:
```bash
python fix_all_issues.py && python tg_bot/bot.py
```

## Troubleshooting

If you encounter issues with the bot, try these steps:

1. Check bot status:
```bash
python check_bot_status.py
```

2. Reset and fix all issues:
```bash
python fix_all_issues.py
```

3. Fix database connection issues:
```bash
python fix_database_connection.py
```

4. Fix integration issues:
```bash
python fix_bot_integration.py
```

## Environment Variables

The bot uses these environment variables:

- `BOT_TOKEN`: Telegram bot token (default: 8102516142:AAFTsVXXujHHKoX2KZGqZXBHPBznfgh7kg0)
- `BOT_USERNAME`: Telegram bot username (default: chan_parsing_mon_bot)
- `API_ID`: Telegram API ID (default: 19840544)
- `API_HASH`: Telegram API Hash (default: c839f28bad345082329ec086fca021fa)

## Database Configuration

The bot supports two database modes:

1. Local SQLite (default for local development)
2. PostgreSQL (default for Railway deployment)

Local configuration happens automatically when you run the bot scripts.

## 🚨 ПРОБЛЕМА: Бот не запускається

Якщо ви бачите помилку:
```
Bot token verification failed: Telegram server says - Unauthorized
```

Це означає, що токен бота недійсний. Необхідно встановити правильний токен.

## 🚀 ШВИДКЕ ВИПРАВЛЕННЯ

```bash
# Запустіть цю команду:
python setup_bot_token.py
```

Слідуйте інструкціям на екрані, щоб налаштувати токен бота.

## 📋 ПОВНИЙ ПРОЦЕС НАЛАШТУВАННЯ

1. **Отримайте токен бота**
   - Відкрийте Telegram і знайдіть @BotFather
   - Відправте /newbot і отримайте токен

2. **Налаштуйте токен**
   - Запустіть `python setup_bot_token.py`
   - Вставте отриманий токен
   - Дочекайтеся підтвердження

3. **Перезапустіть програму**
   - Локально: `python run.py`
   - На Railway: перезапустіть деплоймент

## 📚 ДОДАТКОВА ДОКУМЕНТАЦІЯ

- **Детальні інструкції**: [`НАЛАШТУВАННЯ_БОТА.md`](НАЛАШТУВАННЯ_БОТА.md)
- **Налаштування на Railway**: [`RAILWAY-BOT-SETUP.md`](RAILWAY-BOT-SETUP.md)

## 💡 ПІДКАЗКИ

- Переконайтеся, що бот активний в @BotFather
- Токен має формат як: `123456789:ABCDefGhIJKlmNoPQRsTUVwxyZ`
- Перевірте роботу бота, надіславши йому `/start` в Telegram 