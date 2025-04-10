@echo off
echo Deploying to Railway with template fixes...

:: Check if Python is installed
where python >nul 2>nul
if %ERRORLEVEL% neq 0 (
    echo Python is not installed or not in PATH!
    exit /b 1
)

:: Run our deployment script
python deploy_to_railway.py

:: Check if deployment was successful
if %ERRORLEVEL% neq 0 (
    echo Deployment failed! Check deploy_to_railway.log for details.
    pause
    exit /b 1
)

echo Deployment completed successfully!
echo Visit https://parsinggrouptg-production.up.railway.app/ to see your site.
pause 