@echo off
:: Emergency fix script for Windows
echo === EMERGENCY FIX SCRIPT ===
echo Running emergency fixes for Telegram bot...

:: Install qrcode package
echo Installing qrcode package...
pip install qrcode==7.4.2 --no-cache-dir

:: Fix environment
echo Setting environment variables...
set DJANGO_SETTINGS_MODULE=core.settings

:: Create necessary directories
echo Creating necessary directories...
if not exist logs\bot mkdir logs\bot
if not exist media\messages mkdir media\messages 
if not exist staticfiles\media mkdir staticfiles\media
if not exist data\sessions mkdir data\sessions

:: Fix database and bot imports
echo Running Python fixes...
python fix_bot_emergency.py

:: Run migrations
echo Running database migrations...
python manage.py migrate --noinput

echo === EMERGENCY FIX COMPLETE ===
echo Use 'python direct_start_bot.py' to run the bot directly
pause 