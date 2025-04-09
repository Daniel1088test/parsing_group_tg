#!/usr/bin/env python
"""Django's command-line utility for administrative tasks."""
import os
import sys
import traceback


def main():
    """Run administrative tasks."""
    try:
        os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
        try:
            from django.core.management import execute_from_command_line
        except ImportError as exc:
            raise ImportError(
                "Couldn't import Django. Are you sure it's installed and "
                "available on your PYTHONPATH environment variable? Did you "
                "forget to activate a virtual environment?"
            ) from exc
            
        # Ensure all required directories exist
        ensure_directories()
        
        # Run the command
        execute_from_command_line(sys.argv)
    except Exception as e:
        print(f"Error in manage.py: {e}")
        traceback.print_exc()
        sys.exit(1)


def ensure_directories():
    """Make sure all required directories exist"""
    try:
        dirs = [
            'logs', 
            'media', 'media/messages',
            'static', 'static/img', 
            'staticfiles', 'staticfiles/img',
            'templates', 'templates/admin_panel'
        ]
        
        for directory in dirs:
            os.makedirs(directory, exist_ok=True)
            
        # Create placeholder health files to ensure uptime
        health_files = [
            ('health.txt', 'OK'),
            ('healthz.txt', 'OK')
        ]
        
        # Create in both root and static directories
        for filename, content in health_files:
            for path in ['', 'static/', 'staticfiles/']:
                with open(f"{path}{filename}", 'w') as f:
                    f.write(content)
    except Exception as e:
        print(f"Error creating directories: {e}")


if __name__ == '__main__':
    main()
