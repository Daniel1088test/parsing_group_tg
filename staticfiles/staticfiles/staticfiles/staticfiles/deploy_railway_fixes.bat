@echo off
echo Deploying fixes to Railway...

:: Install required packages
echo Installing required packages...
pip install Pillow

:: Run fix script to ensure templates and migrations are correct
echo Running fix script...
python fix_railway_deployment.py

:: Create basic placeholder PNG files for testing
echo Creating placeholder images...
echo ^<?xml version="1.0" encoding="UTF-8" standalone="no"?^>^<svg width="300" height="200" xmlns="http://www.w3.org/2000/svg"^>^<rect width="298" height="198" x="1" y="1" fill="#f0f0f0" stroke="#c8c8c8" stroke-width="2"/^>^<text x="150" y="110" font-family="Arial" font-size="24" text-anchor="middle" fill="#646464"^>IMAGE^</text^>^</svg^> > staticfiles\img\placeholder-image.svg
echo ^<?xml version="1.0" encoding="UTF-8" standalone="no"?^>^<svg width="300" height="200" xmlns="http://www.w3.org/2000/svg"^>^<rect width="298" height="198" x="1" y="1" fill="#f0f0f0" stroke="#c8c8c8" stroke-width="2"/^>^<text x="150" y="110" font-family="Arial" font-size="24" text-anchor="middle" fill="#646464"^>VIDEO^</text^>^</svg^> > staticfiles\img\placeholder-video.svg

:: Create migration directories if they don't exist
if not exist admin_panel\migrations mkdir admin_panel\migrations

:: Create health check files
echo OK > health.txt
echo OK > health.html
echo OK > healthz.txt
echo OK > healthz.html

:: Create restart trigger
echo Restart triggered at %DATE% %TIME% > railway_restart_trigger.txt

:: Touch wsgi.py to trigger code reload
echo # Restart trigger: %DATE% %TIME% >> core\wsgi.py

:: Git commands to push changes
echo Adding changes to git...
git add .
git commit -m "Fix template rendering and migration issues"

echo Pushing to Railway...
git push railway main

echo Done! Check https://parsinggrouptg-production.up.railway.app/ in a few minutes. 