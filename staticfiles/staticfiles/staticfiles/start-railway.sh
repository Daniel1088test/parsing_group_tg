#!/bin/bash

echo "=== Railway Startup ==="
echo "Running fix requirements script..."
python fix_requirements.py

echo "Setting up environment variables..."
if [ -f .env ]; then
    echo "Loading environment from .env file"
    export $(cat .env | grep -v '^#' | xargs)
fi

# Set Railway environment flag
export RAILWAY_ENVIRONMENT=production

echo "Starting application via run.py..."
python run.py 