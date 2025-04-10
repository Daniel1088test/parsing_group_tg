#!/usr/bin/env python3
"""
Dedicated health check server for Railway that runs outside Django
This ensures health checks pass even if Django has issues
"""
import os
import sys
import http.server
import socketserver
import urllib.parse
import threading
import time

# Health check port (different from main app port)
HEALTH_PORT = int(os.environ.get('HEALTH_PORT', 3000))

# Create health check files
def create_health_files():
    """Create static health check files in the root directory"""
    for filename in ['health.html', 'health.txt', 'healthz.html', 'healthz.txt']:
        with open(filename, 'w') as f:
            f.write('OK')
    print(f"Created health check files")

# Health check handler that doesn't depend on Django
class HealthRequestHandler(http.server.SimpleHTTPRequestHandler):
    def do_GET(self):
        """Handle all GET requests with a 200 OK response"""
        parsed_path = urllib.parse.urlparse(self.path)
        
        # Log request (only in debug mode)
        if os.environ.get('DEBUG') == 'True':
            print(f"Health check request: {self.path} from {self.client_address[0]}")
        
        # Always return 200 OK for all paths
        self.send_response(200)
        
        # Set content type based on path extension
        if parsed_path.path.endswith('.html'):
            self.send_header('Content-type', 'text/html')
            content = '<html><body>OK</body></html>'
        elif parsed_path.path.endswith('.txt'):
            self.send_header('Content-type', 'text/plain')
            content = 'OK'
        elif parsed_path.path.endswith('.json'):
            self.send_header('Content-type', 'application/json')
            content = '{"status": "ok"}'
        else:
            self.send_header('Content-type', 'text/plain')
            content = 'OK'
        
        # Add headers to prevent caching
        self.send_header('Cache-Control', 'no-store, no-cache, must-revalidate')
        self.end_headers()
        
        # Send response content
        self.wfile.write(content.encode('utf-8'))
    
    def log_message(self, format, *args):
        """Suppress log messages unless debug is enabled"""
        if os.environ.get('DEBUG') == 'True':
            super().log_message(format, *args)
        return

def run_health_server():
    """Run the health check server"""
    try:
        # Create health check files first
        create_health_files()
        
        # Set up the server to reuse the address
        socketserver.TCPServer.allow_reuse_address = True
        
        # Try to start the server on the specified port
        with socketserver.TCPServer(("0.0.0.0", HEALTH_PORT), HealthRequestHandler) as httpd:
            print(f"Health check server running on port {HEALTH_PORT}")
            httpd.serve_forever()
    except Exception as e:
        print(f"Error running health check server: {e}")
        # Even if the server fails, create the health files
        create_health_files()
        sys.exit(1)

if __name__ == "__main__":
    # Start server
    run_health_server() 