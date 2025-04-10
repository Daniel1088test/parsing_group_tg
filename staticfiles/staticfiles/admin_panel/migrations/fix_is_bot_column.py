from django.db import migrations, models, connection

def add_is_bot_if_not_exists(apps, schema_editor):
    # Check which database we're using
    vendor = connection.vendor
    cursor = connection.cursor()
    
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
                print("Added is_bot column to admin_panel_telegramsession in PostgreSQL")
        
        elif vendor == 'sqlite':
            # SQLite approach
            cursor.execute("PRAGMA table_info(admin_panel_telegramsession)")
            columns = [info[1] for info in cursor.fetchall()]
            if 'is_bot' not in columns:
                cursor.execute("""
                    ALTER TABLE admin_panel_telegramsession 
                    ADD COLUMN is_bot BOOLEAN DEFAULT 0
                """)
                print("Added is_bot column to admin_panel_telegramsession in SQLite")
    except Exception as e:
        print(f"Error adding is_bot column: {e}")
    finally:
        cursor.close()

class Migration(migrations.Migration):

    dependencies = [
        ("admin_panel", "fix_session_name_column"),
    ]

    operations = [
        migrations.RunPython(add_is_bot_if_not_exists),
    ] 