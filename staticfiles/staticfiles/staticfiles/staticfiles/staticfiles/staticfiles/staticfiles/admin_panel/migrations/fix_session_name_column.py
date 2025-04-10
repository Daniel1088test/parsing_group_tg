from django.db import migrations, models, connection

def add_session_name_if_not_exists(apps, schema_editor):
    # Check which database we're using
    vendor = connection.vendor
    cursor = connection.cursor()
    
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
                print("Added session_name column to admin_panel_telegramsession in PostgreSQL")
        
        elif vendor == 'sqlite':
            # SQLite approach
            cursor.execute("PRAGMA table_info(admin_panel_telegramsession)")
            columns = [info[1] for info in cursor.fetchall()]
            if 'session_name' not in columns:
                cursor.execute("""
                    ALTER TABLE admin_panel_telegramsession 
                    ADD COLUMN session_name VARCHAR(255) DEFAULT 'default'
                """)
                print("Added session_name column to admin_panel_telegramsession in SQLite")
    except Exception as e:
        print(f"Error adding session_name column: {e}")
    finally:
        cursor.close()

class Migration(migrations.Migration):

    dependencies = [
        ("admin_panel", "0009_merge_20250409_0025"),
    ]

    operations = [
        migrations.RunPython(add_session_name_if_not_exists),
    ] 