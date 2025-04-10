@echo off
echo Starting database migration...

REM Run test connection script
python test_db_connection.py

if %ERRORLEVEL% NEQ 0 (
    echo Database connection test failed. Aborting migration.
    exit /b 1
)

REM Run migrations
echo Running migrations...
python manage.py migrate

if %ERRORLEVEL% NEQ 0 (
    echo Migration failed.
    exit /b 1
) else (
    echo Migration completed successfully.
) 