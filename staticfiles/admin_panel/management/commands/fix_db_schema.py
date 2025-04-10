import logging
from django.core.management.base import BaseCommand
from django.db import connection

logger = logging.getLogger(__name__)

class Command(BaseCommand):
    help = 'Fix database schema issues including missing columns'

    def add_arguments(self, parser):
        parser.add_argument(
            '--quiet',
            action='store_true',
            dest='quiet',
            default=False,
            help='Suppress output messages',
        )

    def handle(self, *args, **options):
        quiet = options.get('quiet', False)
        
        # Fix session_name column
        self.fix_session_name_column(quiet)
        
        # Fix is_bot column
        self.fix_is_bot_column(quiet)
        
        if not quiet:
            self.stdout.write(self.style.SUCCESS('Database schema fixed successfully'))
    
    def fix_session_name_column(self, quiet):
        """Add session_name column if it doesn't exist"""
        
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
                    if not quiet:
                        self.stdout.write(self.style.SUCCESS('Added session_name column to admin_panel_telegramsession'))
            
            elif vendor == 'sqlite':
                # SQLite approach
                cursor.execute("PRAGMA table_info(admin_panel_telegramsession)")
                columns = [info[1] for info in cursor.fetchall()]
                if 'session_name' not in columns:
                    cursor.execute("""
                        ALTER TABLE admin_panel_telegramsession 
                        ADD COLUMN session_name VARCHAR(255) DEFAULT 'default'
                    """)
                    if not quiet:
                        self.stdout.write(self.style.SUCCESS('Added session_name column to admin_panel_telegramsession'))
        except Exception as e:
            logger.error(f"Error adding session_name column: {e}")
            if not quiet:
                self.stdout.write(self.style.ERROR(f'Error adding session_name column: {e}'))
        finally:
            cursor.close()
            
    def fix_is_bot_column(self, quiet):
        """Add is_bot column if it doesn't exist"""
        
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
                    if not quiet:
                        self.stdout.write(self.style.SUCCESS('Added is_bot column to admin_panel_telegramsession'))
            
            elif vendor == 'sqlite':
                # SQLite approach
                cursor.execute("PRAGMA table_info(admin_panel_telegramsession)")
                columns = [info[1] for info in cursor.fetchall()]
                if 'is_bot' not in columns:
                    cursor.execute("""
                        ALTER TABLE admin_panel_telegramsession 
                        ADD COLUMN is_bot BOOLEAN DEFAULT 0
                    """)
                    if not quiet:
                        self.stdout.write(self.style.SUCCESS('Added is_bot column to admin_panel_telegramsession'))
        except Exception as e:
            logger.error(f"Error adding is_bot column: {e}")
            if not quiet:
                self.stdout.write(self.style.ERROR(f'Error adding is_bot column: {e}'))
        finally:
            cursor.close() 