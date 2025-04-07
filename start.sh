#!/bin/bash

# Database settings - use these if DATABASE_URL is not set
if [ -z "$DATABASE_URL" ]; then
    echo "DATABASE_URL not found, setting it manually..."
    export DATABASE_URL="postgresql://postgres:urCNhXdwvbqOvvEsJDffIiDUMcLhAvcs@switchback.proxy.rlwy.net:10052/railway"
fi

# Run migrations first
bash migrate.sh

# Start the application
echo "Starting application..."
python run.py 