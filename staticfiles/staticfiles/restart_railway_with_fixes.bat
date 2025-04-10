@echo off
echo Deploying template fixes to Railway...

:: Create restart trigger for Railway
echo Creating restart trigger...
echo "Restart triggered at %DATE% %TIME%" > railway_restart_trigger.txt

:: Touch the wsgi.py file to trigger restart
echo Touching wsgi.py to trigger code reloading...
echo # Restart trigger: %DATE% %TIME% >> core\wsgi.py

:: Create health check files
echo Creating health check files...
echo OK > health.html
echo OK > healthz.html
echo OK > health.txt
echo OK > healthz.txt

:: Push changes to Railway
echo Adding changes to git...
git add .
git commit -m "Fix templates and URL routing issues"

echo Pushing to Railway...
git push railway main

echo Done! Check https://parsinggrouptg-production.up.railway.app/ in a few minutes. 