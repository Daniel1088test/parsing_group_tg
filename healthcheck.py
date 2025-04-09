#!/usr/bin/env python3
"""
Healthcheck script to verify deployment settings
"""
import os
import sys
import json

# Add current directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Display environment information
def main():
    """Display deployment environment information"""
    print("=== Deployment Environment Check ===")
    
    # Get Django settings
    try:
        os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
        import django
        django.setup()
        from django.conf import settings
        
        # Display allowed hosts
        print(f"ALLOWED_HOSTS: {settings.ALLOWED_HOSTS}")
        
        # Display CSRF settings
        if hasattr(settings, 'CSRF_TRUSTED_ORIGINS'):
            print(f"CSRF_TRUSTED_ORIGINS: {settings.CSRF_TRUSTED_ORIGINS}")
        
        # Check Railway variables
        railway_domain = os.environ.get('RAILWAY_PUBLIC_DOMAIN', 'Not set')
        print(f"RAILWAY_PUBLIC_DOMAIN: {railway_domain}")
        
        # Create a health check file
        with open('healthcheck.txt', 'w') as f:
            f.write(f"Healthcheck passed. ALLOWED_HOSTS: {settings.ALLOWED_HOSTS}")
        
        # Create HTML version too
        with open('health.html', 'w') as f:
            f.write("OK")
        
        # Create plain text version
        with open('health.txt', 'w') as f:
            f.write("OK")
        
        # Create standard Rails-style health endpoints
        with open('healthz.html', 'w') as f:
            f.write("OK")
        
        with open('healthz.txt', 'w') as f:
            f.write("OK")
        
        print("Healthcheck files created successfully.")
        
        return True
    except Exception as e:
        print(f"ERROR: {e}")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1) 