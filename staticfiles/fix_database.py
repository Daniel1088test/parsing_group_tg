#!/usr/bin/env python
"""
Script to fix database schema issues by adding missing columns.
Run this script directly to apply fixes to the database.
"""

import os
import sys
import django
from django.db import connection

# Setup Django
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()

def fix_session_name_column():
    """Add session_name column if it doesn't exist"""
    vendor = connection.vendor
    cursor = connection.cursor()
    column_added = False
    
    try:
        if vendor == 'postgresql':
            # PostgreSQL approach
            cursor.execute("""
                SELECT column_name FROM information_schema.columns 
                WHERE table_name = 'admin_panel_telegramsession' 
                AND column_name = 'session_name'
            """)
            if not cursor.fetchone():
                cursor.execute("""
                    ALTER TABLE admin_panel_telegramsession 
                    ADD COLUMN session_name VARCHAR(255) DEFAULT 'default'
                """)
                print("✓ Added session_name column to admin_panel_telegramsession")
                column_added = True
            else:
                print("✓ session_name column already exists")
        
        elif vendor == 'sqlite':
            # SQLite approach
            cursor.execute("PRAGMA table_info(admin_panel_telegramsession)")
            columns = [info[1] for info in cursor.fetchall()]
            if 'session_name' not in columns:
                cursor.execute("""
                    ALTER TABLE admin_panel_telegramsession 
                    ADD COLUMN session_name VARCHAR(255) DEFAULT 'default'
                """)
                print("✓ Added session_name column to admin_panel_telegramsession")
                column_added = True
            else:
                print("✓ session_name column already exists")
    except Exception as e:
        print(f"✕ Error adding session_name column: {e}")
    finally:
        cursor.close()
    
    return column_added

def fix_is_bot_column():
    """Add is_bot column if it doesn't exist"""
    vendor = connection.vendor
    cursor = connection.cursor()
    column_added = False
    
    try:
        if vendor == 'postgresql':
            # PostgreSQL approach
            cursor.execute("""
                SELECT column_name FROM information_schema.columns 
                WHERE table_name = 'admin_panel_telegramsession' 
                AND column_name = 'is_bot'
            """)
            if not cursor.fetchone():
                cursor.execute("""
                    ALTER TABLE admin_panel_telegramsession 
                    ADD COLUMN is_bot BOOLEAN DEFAULT FALSE
                """)
                print("✓ Added is_bot column to admin_panel_telegramsession")
                column_added = True
            else:
                print("✓ is_bot column already exists")
        
        elif vendor == 'sqlite':
            # SQLite approach
            cursor.execute("PRAGMA table_info(admin_panel_telegramsession)")
            columns = [info[1] for info in cursor.fetchall()]
            if 'is_bot' not in columns:
                cursor.execute("""
                    ALTER TABLE admin_panel_telegramsession 
                    ADD COLUMN is_bot BOOLEAN DEFAULT 0
                """)
                print("✓ Added is_bot column to admin_panel_telegramsession")
                column_added = True
            else:
                print("✓ is_bot column already exists")
    except Exception as e:
        print(f"✕ Error adding is_bot column: {e}")
    finally:
        cursor.close()
    
    return column_added

if __name__ == "__main__":
    print(f"Using {connection.vendor} database")
    
    # Fix session_name column
    session_name_fixed = fix_session_name_column()
    
    # Fix is_bot column
    is_bot_fixed = fix_is_bot_column()
    
    # Apply migrations
    try:
        from django.core.management import call_command
        print("\nApplying migrations...")
        call_command('migrate', 'admin_panel')
        print("✓ Migrations applied successfully")
    except Exception as e:
        print(f"✕ Error applying migrations: {e}")
    
    # Final report
    if session_name_fixed or is_bot_fixed:
        print("\n✓ Database schema has been fixed.")
    else:
        print("\n✓ Database schema was already correct.")
    
    print("\nTo start the application with the bot, run:")
    print("python manage.py start_all") 