#!/bin/bash
# Script to run the bot connection fix and then restart the bot

echo "=== Starting bot fix process ==="
date

# Make script executable
chmod +x fix_bot_connection.py

# Kill any existing bot processes to start fresh
echo "Stopping existing bot processes..."
pkill -f "run_bot.py" || echo "No run_bot.py processes found"
pkill -f "python.*bot\.py" || echo "No bot.py processes found"
pkill -f "direct_bot" || echo "No direct_bot processes found"
sleep 2

# Run the fix script
echo "Running database and connection fix..."
python fix_bot_connection.py
if [ $? -eq 0 ]; then
    echo "✅ Fix completed successfully"
else
    echo "⚠️ Fix encountered issues but continuing"
fi

# Make log directory
mkdir -p logs/bot

# Start the bot with detailed logging
echo "Starting bot with enhanced logging..."
nohup python run_bot.py > logs/bot/restart_bot.log 2>&1 &
BOT_PID=$!
echo $BOT_PID > restart_bot.pid
echo "Bot started with PID: $BOT_PID"

# Wait a moment for the bot to initialize
sleep 10

# Check if bot is still running
if ps -p $BOT_PID > /dev/null; then
    echo "✅ Bot is still running after 10 seconds"
else
    echo "❌ Bot process terminated - check logs/bot/restart_bot.log"
    cat logs/bot/restart_bot.log | tail -n 20
fi

# Check if connection was verified
if [ -f "bot_verified.flag" ]; then
    echo "✅ Bot connection was verified:"
    cat bot_verified.flag
else
    echo "❌ Bot verification failed - no verification flag found"
fi

echo "=== Bot fix process completed ==="
date 