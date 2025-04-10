@echo off
echo Restarting Railway application...

:: Run the Python restart script
python restart_railway.py

:: Git commands to push changes
echo Adding changes to git...
git add .
git commit -m "Update index template to use full-featured design"

echo Pushing to Railway...
git push railway main

echo Done! Your application should restart with the new template.
echo Check https://parsinggrouptg-production.up.railway.app/ in a few minutes. 