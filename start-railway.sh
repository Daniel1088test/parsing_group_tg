#!/bin/bash
set -e

echo "===================== Starting Railway Deployment ====================="

# Export needed environment variables 
echo "Setting up environment variables..."
export RAILWAY_PUBLIC_DOMAIN=${RAILWAY_PUBLIC_DOMAIN:-"parsinggrouptg-production.up.railway.app"}
export PORT=${PORT:-8080}

# Fix requirements.txt if needed (додатковий рівень захисту)
echo "Checking requirements.txt for conflicts..."
if [ -f "fix_requirements.py" ]; then
    python fix_requirements.py
    if [ $? -ne 0 ]; then
        echo "Warning: Could not fix requirements.txt, but continuing"
    else
        echo "Requirements check completed"
    fi
fi

# Make scripts executable
chmod +x migrate-railway.py
chmod +x run_bot.py
chmod +x run_parser.py

# Run our enhanced migration script that handles errors and prepares media paths
echo "Running enhanced migration script..."
python migrate-railway.py

# Extra safety measure: check if media directories exist
echo "Ensuring media directories exist..."
mkdir -p media/messages
mkdir -p staticfiles/media
mkdir -p logs/bot
mkdir -p data/sessions

# Set directory permissions
echo "Setting directory permissions..."
chmod -R 755 media
chmod -R 755 staticfiles
chmod -R 755 logs
chmod -R 755 data

# Print environment information
echo "Environment information:"
echo "PORT: $PORT"
echo "RAILWAY_PUBLIC_DOMAIN: $RAILWAY_PUBLIC_DOMAIN"
echo "PUBLIC_URL: $PUBLIC_URL"

# Ensure health check files
echo "ok" > health.txt
echo "ok" > health.html
echo "ok" > healthz.txt
echo "ok" > healthz.html

# Start the Telegram bot in background with proper logging
echo "Starting Telegram bot in background..."
nohup python run_bot.py > logs/bot/bot.log 2>&1 &
BOT_PID=$!
echo "Bot started with PID: $BOT_PID"

# Start the Telegram parser in background with proper logging
echo "Starting Telegram parser in background..."
nohup python run_parser.py > logs/bot/parser.log 2>&1 &
PARSER_PID=$!
echo "Parser started with PID: $PARSER_PID"

# Give the background processes a moment to start and check if they're running
sleep 2
ps -p $BOT_PID >/dev/null && echo "Bot is running correctly" || echo "Warning: Bot may have failed to start"
ps -p $PARSER_PID >/dev/null && echo "Parser is running correctly" || echo "Warning: Parser may have failed to start"

# Create PID files for service monitoring
echo $BOT_PID > bot.pid
echo $PARSER_PID > parser.pid

# Create a simple healthcheck endpoint
cat > healthcheck.py << 'EOF'
#!/usr/bin/env python3
import os
import sys
import subprocess
import time
import logging
from http.server import HTTPServer, BaseHTTPRequestHandler

class HealthHandler(BaseHTTPRequestHandler):
    def _set_headers(self, status_code=200):
        self.send_response(status_code)
        self.send_header('Content-type', 'text/plain')
        self.end_headers()

    def do_GET(self):
        # Check if bot and parser are running
        bot_status = "Unknown"
        parser_status = "Unknown"

        try:
            with open('bot.pid', 'r') as f:
                bot_pid = f.read().strip()
                if bot_pid and subprocess.run(['ps', '-p', bot_pid], stdout=subprocess.PIPE).returncode == 0:
                    bot_status = "Running"
                else:
                    bot_status = "Stopped"
        except:
            bot_status = "Error"

        try:
            with open('parser.pid', 'r') as f:
                parser_pid = f.read().strip()
                if parser_pid and subprocess.run(['ps', '-p', parser_pid], stdout=subprocess.PIPE).returncode == 0:
                    parser_status = "Running"
                else:
                    parser_status = "Stopped"
        except:
            parser_status = "Error"

        # Return basic response for health check endpoints
        if self.path in ['/health', '/healthz', '/health/', '/healthz/', '/ping']:
            self._set_headers()
            self.wfile.write(b"ok")
            return

        # For the status endpoint, return more info
        if self.path == '/status':
            self._set_headers()
            status = f"Bot: {bot_status}\nParser: {parser_status}\nTimestamp: {time.strftime('%Y-%m-%d %H:%M:%S')}\n"
            self.wfile.write(status.encode())
            return

        # Default case
        self._set_headers(404)
        self.wfile.write(b"Not found")

def run_health_server(port=8081):
    server_address = ('', port)
    httpd = HTTPServer(server_address, HealthHandler)
    print(f"Starting health check server on port {port}")
    httpd.serve_forever()

if __name__ == "__main__":
    # Get port from environment or use default
    port = int(os.environ.get('HEALTH_PORT', 8081))
    run_health_server(port)
EOF

# Start the health check server in background
chmod +x healthcheck.py
nohup python healthcheck.py > logs/health.log 2>&1 &
HEALTH_PID=$!
echo "Health check server started with PID: $HEALTH_PID"

# Start the Django server
echo "Starting Django server on 0.0.0.0:$PORT..."
exec python manage.py runserver 0.0.0.0:$PORT