@echo off
echo Pushing fixes to Railway...

:: First create health files for Railway
echo Creating health files...
python healthcheck.py

:: Run restart trigger
echo Creating restart trigger...
python restart_railway.py

:: Git commands
echo Adding files to git...
git add .
git commit -m "Fix admin panel template, session corruption, and unclosed aiohttp sessions"

echo Pushing to Railway...
git push railway main

echo Done! Changes should deploy automatically.
echo Check your Railway dashboard for deployment status. 