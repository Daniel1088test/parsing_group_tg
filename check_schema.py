#!/usr/bin/env python
import os
import sys
import django

# Setup Django
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()

from django.db import connection
with connection.cursor() as cursor:
    cursor.execute('PRAGMA table_info(admin_panel_telegramsession)')
    columns = [info[1] for info in cursor.fetchall()]
    print('Existing columns:')
    for col in columns:
        print(f'  - {col}')
    
    # Check if is_bot exists
    if 'is_bot' not in columns:
        print("\nAdding is_bot column...")
        cursor.execute("""
            ALTER TABLE admin_panel_telegramsession 
            ADD COLUMN is_bot BOOLEAN DEFAULT 0
        """)
        print("✓ Added is_bot column successfully")
    else:
        print("\nis_bot column already exists") 