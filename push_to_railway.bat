@echo off
echo Pushing fixes to Railway...

:: First create health files for Railway
echo Creating health files...
python healthcheck.py

:: Git commands
echo Adding files to git...
git add .
git commit -m "Fix DisallowedHost error by adding Railway domain to ALLOWED_HOSTS"

echo Pushing to Railway...
git push railway main

echo Done! Changes should deploy automatically.
echo Check your Railway dashboard for deployment status. 