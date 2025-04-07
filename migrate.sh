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
    python -c "
import os
import sys
import psycopg
from urllib.parse import urlparse

db_url = urlparse(os.getenv('DATABASE_URL'))
print(f'Connecting to PostgreSQL: {db_url.hostname}:{db_url.port}/{db_url.path[1:]}')

try:
    conn = psycopg.connect(
        host=db_url.hostname,
        port=db_url.port,
        dbname=db_url.path[1:],
        user=db_url.username,
        password=db_url.password
    )
    print('Connection successful!')
    conn.close()
except Exception as e:
    print(f'Connection error: {e}')
    sys.exit(1)
"
    
    # If we get here, the connection was successful
    echo "Database connection test passed."
    
    # Run migrations
    echo "Running migrations..."
    python manage.py migrate
fi

# Check if migrations were successful
if [ $? -ne 0 ]; then
    echo "Migration failed."
    exit 1
else
    echo "Migration completed successfully."
fi 