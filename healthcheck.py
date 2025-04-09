#!/usr/bin/env python
"""
Simple health check server for Railway
Always returns 200 OK to allow the container to keep running
"""
import os
import sys
import http.server
import socketserver
from datetime import datetime

# Get port from environment or use default
PORT = int(os.environ.get('HEALTH_PORT', 8000))

class HealthCheckHandler(http.server.SimpleHTTPRequestHandler):
    """Health check request handler that always returns OK"""
    
    def do_GET(self):
        """Handle GET request by returning 200 OK"""
        # Always respond with 200 OK
        self.send_response(200)
        self.send_header('Content-type', 'text/html')
        self.end_headers()
        
        # Get server info
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        health_message = f"""
        <html>
        <head><title>Health Check OK</title></head>
        <body>
            <h1>Health Check: OK</h1>
            <p>Timestamp: {timestamp}</p>
            <p>Path: {self.path}</p>
            <p>Server is running and accepting requests.</p>
        </body>
        </html>
        """
        
        self.wfile.write(health_message.encode())
        
    def log_message(self, format, *args):
        """Override to reduce logging noise"""
        # Only log health check requests if DEBUG is enabled
        if os.environ.get('DEBUG') == 'True':
            super().log_message(format, *args)

def run_health_server():
    """Run a simple HTTP server for health checks"""
    try:
        with socketserver.TCPServer(("", PORT), HealthCheckHandler) as httpd:
            print(f"Health check server started at port {PORT}")
            httpd.serve_forever()
    except KeyboardInterrupt:
        print("Health check server stopped by user")
        sys.exit(0)
    except Exception as e:
        print(f"Error running health check server: {e}")
        sys.exit(1)

if __name__ == "__main__":
    run_health_server() 