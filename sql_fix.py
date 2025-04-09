#!/usr/bin/env python3
"""
Direct SQL fix for migration issues
This script directly marks migrations as completed in the database
"""
import os
import sys
import django
from django.db import connection, DatabaseError

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()

def fix_migrations():
    """Fix the migration records directly in the database"""
    try:
        print("Running direct SQL fix for migrations...")
        with connection.cursor() as cursor:
            # Check if the django_migrations table exists
            cursor.execute("SELECT to_regclass('public.django_migrations');")
            if cursor.fetchone()[0]:
                # Get current migrations
                cursor.execute("SELECT id, app, name FROM django_migrations WHERE app='admin_panel';")
                existing_migrations = cursor.fetchall()
                print(f"Found {len(existing_migrations)} existing migrations for admin_panel:")
                for migration in existing_migrations:
                    print(f"  {migration[0]}: {migration[1]}.{migration[2]}")
                
                # Required migrations that should be marked as applied
                required_migrations = [
                    '0001_initial',
                    '0002_auto_20250409_0000',
                    'fix_is_bot_column',
                    '0003_merge_final',
                    '0004_fake_migration'
                ]
                
                # Get existing migration names
                existing_names = [row[2] for row in existing_migrations]
                
                # Add missing migrations
                for migration in required_migrations:
                    if migration not in existing_names:
                        print(f"Adding missing migration: admin_panel.{migration}")
                        cursor.execute(
                            "INSERT INTO django_migrations (app, name, applied) VALUES (%s, %s, now());",
                            ['admin_panel', migration]
                        )
                
                print("Migration records fixed successfully")
                return True
            else:
                print("django_migrations table does not exist, cannot fix directly")
                return False
    except DatabaseError as e:
        print(f"Database error: {e}")
        return False
    except Exception as e:
        print(f"Error: {e}")
        return False

if __name__ == "__main__":
    success = fix_migrations()
    sys.exit(0 if success else 1) 