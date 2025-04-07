#!/bin/bash

echo "Starting database migration..."

# Run test connection script
python test_db_connection.py

if [ $? -ne 0 ]; then
    echo "Database connection test failed. Aborting migration."
    exit 1
fi

# Run migrations
echo "Running migrations..."
python manage.py migrate

# Check if migrations were successful
if [ $? -ne 0 ]; then
    echo "Migration failed."
    exit 1
else
    echo "Migration completed successfully."
fi 