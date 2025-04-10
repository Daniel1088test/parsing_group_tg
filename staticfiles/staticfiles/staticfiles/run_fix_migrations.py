#!/usr/bin/env python
import os
import sys
import django

# Add the project directory to the Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Set up Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()

def run_migrations():
    """Run migrations to fix database schema issues"""
    try:
        print("Applying migrations to fix database schema...")
        from django.core.management import call_command
        call_command('migrate', 'admin_panel')
        print("Migrations applied successfully!")
        return True
    except Exception as e:
        print(f"Error applying migrations: {e}")
        return False

if __name__ == "__main__":
    success = run_migrations()
    sys.exit(0 if success else 1) 