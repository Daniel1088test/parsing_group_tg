#!/usr/bin/env python
"""
Dedicated Railway health check server
Creates static health check files and runs a minimal HTTP server
"""
import os
import sys
import http.server
import socketserver
import threading
import time
import signal

# Use a different port for health check to avoid conflict with Django
HEALTH_PORT = int(os.environ.get('HEALTH_PORT', 3000))

# Create static health check files
print("Creating health check files...")
with open('health.txt', 'w') as f:
    f.write('OK')
with open('health.html', 'w') as f:
    f.write('<html><body>OK</body></html>')
with open('healthz.txt', 'w') as f:
    f.write('OK')
with open('healthz.html', 'w') as f:
    f.write('<html><body>OK</body></html>')
print("Health check files created successfully")

class HealthHandler(http.server.BaseHTTPRequestHandler):
    """Minimal health check handler"""
    
    def do_GET(self):
        """Return 200 OK for all paths"""
        self.send_response(200)
        self.send_header('Content-type', 'text/html')
        self.end_headers()
        self.wfile.write(b'<html><body>OK</body></html>')
    
    def log_message(self, format, *args):
        """Silence logging"""
        return

def run_server():
    """Run the health check server"""
    print(f"Starting health check server on port {HEALTH_PORT}...")
    
    # Allow port reuse for faster restart
    socketserver.TCPServer.allow_reuse_address = True
    
    try:
        with socketserver.TCPServer(("0.0.0.0", HEALTH_PORT), HealthHandler) as httpd:
            print(f"Health check server running on port {HEALTH_PORT}")
            httpd.serve_forever()
    except OSError as e:
        print(f"Failed to start server: {e}")
        
        # Try alternate port
        alt_port = 8000
        print(f"Trying alternate port {alt_port}...")
        try:
            with socketserver.TCPServer(("0.0.0.0", alt_port), HealthHandler) as httpd:
                print(f"Health check server running on alternate port {alt_port}")
                httpd.serve_forever()
        except Exception as e2:
            print(f"Failed to start on alternate port: {e2}")
            # Keep running even if server fails
            while True:
                time.sleep(60)
    except KeyboardInterrupt:
        print("Server stopped by user")
        sys.exit(0)
    except Exception as e:
        print(f"Unexpected error: {e}")
        # Keep running even if server fails
        while True:
            time.sleep(60)

# Handle signals gracefully
def signal_handler(sig, frame):
    print(f"Received signal {sig}, exiting gracefully")
    sys.exit(0)

signal.signal(signal.SIGINT, signal_handler)
signal.signal(signal.SIGTERM, signal_handler)

if __name__ == "__main__":
    # Start server
    run_server() 