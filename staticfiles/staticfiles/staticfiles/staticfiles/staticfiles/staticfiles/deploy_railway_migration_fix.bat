@echo off
echo Deploying emergency migration fix to Railway...

:: Create placeholder files to ensure assets exist
echo Creating placeholder assets...
mkdir staticfiles\img 2>nul
echo ^<?xml version="1.0" encoding="UTF-8" standalone="no"?^>^<svg width="300" height="200" xmlns="http://www.w3.org/2000/svg"^>^<rect width="298" height="198" x="1" y="1" fill="#f0f0f0" stroke="#c8c8c8" stroke-width="2"/^>^<text x="150" y="110" font-family="Arial" font-size="24" text-anchor="middle" fill="#646464"^>IMAGE^</text^>^</svg^> > staticfiles\img\placeholder-image.svg
echo ^<?xml version="1.0" encoding="UTF-8" standalone="no"?^>^<svg width="300" height="200" xmlns="http://www.w3.org/2000/svg"^>^<rect width="298" height="198" x="1" y="1" fill="#f0f0f0" stroke="#c8c8c8" stroke-width="2"/^>^<text x="150" y="110" font-family="Arial" font-size="24" text-anchor="middle" fill="#646464"^>VIDEO^</text^>^</svg^> > staticfiles\img\placeholder-video.svg

:: Create health check files
echo Creating health check files...
echo OK > health.txt
echo OK > health.html
echo OK > healthz.txt
echo OK > healthz.html

:: Create restart trigger
echo Creating restart trigger...
echo Restart triggered at %DATE% %TIME% > railway_restart_trigger.txt

:: Add restart marker to WSGI file
echo # Restart trigger: %DATE% %TIME% >> core\wsgi.py

:: Git commands
echo Adding changes to git...
git add .
git commit -m "Fix migration issues with needs_auth column"

echo Pushing to origin (for Railway)...
git push origin main

echo Done! Railway should detect the changes and restart.
echo Check https://parsinggrouptg-production.up.railway.app/ in a few minutes. 