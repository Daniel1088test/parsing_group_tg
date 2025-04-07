#!/bin/bash

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
    # Run test connection script
    python test_db_connection.py
    
    if [ $? -ne 0 ]; then
        echo "Database connection test failed, but continuing with migrations..."
    fi
    
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