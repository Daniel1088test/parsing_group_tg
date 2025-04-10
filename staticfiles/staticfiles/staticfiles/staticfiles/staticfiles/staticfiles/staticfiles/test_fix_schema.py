#!/usr/bin/env python
import os
import sys
import django

# Setup Django
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()

from django.db import connection

def check_session_name_column():
    """Check if the session_name column exists in the TelegramSession table"""
    with connection.cursor() as cursor:
        vendor = connection.vendor
        
        if vendor == 'postgresql':
            cursor.execute("""
                SELECT column_name FROM information_schema.columns 
                WHERE table_name = 'admin_panel_telegramsession' 
                AND column_name = 'session_name'
            """)
            exists = cursor.fetchone() is not None
        elif vendor == 'sqlite':
            cursor.execute("PRAGMA table_info(admin_panel_telegramsession)")
            columns = [info[1] for info in cursor.fetchall()]
            exists = 'session_name' in columns
        else:
            print(f"Unsupported database vendor: {vendor}")
            return False
        
        if exists:
            print("✅ session_name column exists in the TelegramSession table")
            return True
        else:
            print("❌ session_name column does NOT exist in the TelegramSession table")
            return False

if __name__ == "__main__":
    print(f"Using {connection.vendor} database")
    
    # Check if session_name column exists
    result = check_session_name_column()
    
    # Try to query the TelegramSession model
    try:
        from admin_panel.models import TelegramSession
        sessions = TelegramSession.objects.all()
        print(f"✅ Successfully queried TelegramSession model. Found {len(sessions)} sessions.")
        print("Sample session fields:", ", ".join([field.name for field in TelegramSession._meta.fields[:5]]))
    except Exception as e:
        print(f"❌ Error querying TelegramSession model: {e}")
    
    # Exit with status code
    sys.exit(0 if result else 1) 