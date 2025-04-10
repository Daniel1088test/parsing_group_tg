#!/bin/bash

# Make script exit on any error
set -e

echo "Starting database migration..."

# Check if DATABASE_URL is set
if [ -z "$DATABASE_URL" ]; then
    echo "WARNING: DATABASE_URL environment variable not found."
    echo "Make sure you've set the DATABASE_URL in Railway dashboard."
    echo "Using Django's default database settings instead."
    
    # Continue with migrations without running test
    echo "Running migrations with default settings..."
    python manage.py migrate
else
    # First try a basic connection check
    echo "Testing database connection..."
    set +e  # Don't exit on error
    python -c "
import os
import sys
import time
import psycopg
from urllib.parse import urlparse

db_url = urlparse(os.getenv('DATABASE_URL'))
print(f'Connecting to PostgreSQL: {db_url.hostname}:{db_url.port}/{db_url.path[1:]}')

# Try multiple times with backoff
max_attempts = 5
for attempt in range(1, max_attempts + 1):
    try:
        conn = psycopg.connect(
            host=db_url.hostname,
            port=db_url.port,
            dbname=db_url.path[1:],
            user=db_url.username,
            password=db_url.password,
            connect_timeout=10
        )
        print('Connection successful!')
        conn.close()
        sys.exit(0)
    except Exception as e:
        print(f'Connection attempt {attempt} failed: {e}')
        if attempt < max_attempts:
            wait_time = 2 ** attempt  # Exponential backoff
            print(f'Retrying in {wait_time} seconds...')
            time.sleep(wait_time)
        else:
            print('All connection attempts failed')
            sys.exit(1)
"
    DB_CONNECTION_RESULT=$?
    set -e  # Re-enable exit on error
    
    if [ $DB_CONNECTION_RESULT -ne 0 ]; then
        echo "WARNING: Database connection test failed, but continuing with migrations anyway..."
    else
        echo "Database connection test passed."
    fi
    
    # Run migrations
    echo "Running migrations..."
    set +e  # Don't exit on error for migrations
    python manage.py migrate
    MIGRATE_RESULT=$?
    set -e  # Re-enable exit on error
    
    if [ $MIGRATE_RESULT -ne 0 ]; then
        echo "WARNING: Migration failed, but continuing with startup..."
    else
        echo "Migration completed successfully."
    fi
    
    exit 0  # Always exit successfully to allow the application to start
fi 