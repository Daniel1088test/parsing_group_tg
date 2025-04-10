import os
import sys
import logging
from django.core.management.base import BaseCommand
from django.db import connection, transaction
from django.conf import settings

class Command(BaseCommand):
    help = 'Debug and fix database connection issues'
    
    def add_arguments(self, parser):
        parser.add_argument(
            '--check-only',
            action='store_true',
            help='Only check database, do not make changes',
        )
    
    def handle(self, *args, **options):
        check_only = options.get('check_only', False)
        
        self.stdout.write(self.style.SUCCESS('=== Database Debug Tool ==='))
        self.stdout.write(f'Django settings module: {settings.SETTINGS_MODULE}')
        self.stdout.write(f'Database engine: {settings.DATABASES["default"]["ENGINE"]}')
        
        # Check database connection
        self.stdout.write('Checking database connection...')
        try:
            with connection.cursor() as cursor:
                cursor.execute('SELECT 1')
                self.stdout.write(self.style.SUCCESS('✓ Database connection works'))
                
                # Check BotSettings table
                cursor.execute("""
                    SELECT EXISTS (
                        SELECT FROM information_schema.tables 
                        WHERE table_name='admin_panel_botsettings'
                    ) AS table_exists
                """)
                table_exists = cursor.fetchone()[0]
                
                if table_exists:
                    self.stdout.write(self.style.SUCCESS('✓ BotSettings table exists'))
                    
                    # Check columns
                    cursor.execute("""
                        SELECT column_name FROM information_schema.columns 
                        WHERE table_name='admin_panel_botsettings'
                    """)
                    columns = [row[0] for row in cursor.fetchall()]
                    self.stdout.write(f'Columns: {", ".join(columns)}')
                    
                    # Check for missing columns
                    missing_columns = []
                    for column in ['bot_username', 'welcome_message', 'auth_guide_text', 'menu_style']:
                        if column not in columns:
                            missing_columns.append(column)
                    
                    if missing_columns:
                        self.stdout.write(self.style.WARNING(f'Missing columns: {", ".join(missing_columns)}'))
                        
                        if not check_only:
                            self.stdout.write('Adding missing columns...')
                            for column in missing_columns:
                                try:
                                    if column == 'bot_username':
                                        cursor.execute('ALTER TABLE admin_panel_botsettings ADD COLUMN bot_username VARCHAR(255) NULL')
                                    elif column in ['welcome_message', 'auth_guide_text']:
                                        cursor.execute(f'ALTER TABLE admin_panel_botsettings ADD COLUMN {column} TEXT NULL')
                                    elif column == 'menu_style':
                                        cursor.execute('ALTER TABLE admin_panel_botsettings ADD COLUMN menu_style VARCHAR(50) NULL')
                                    
                                    self.stdout.write(self.style.SUCCESS(f'✓ Added {column} column'))
                                except Exception as e:
                                    self.stdout.write(self.style.ERROR(f'Error adding {column}: {e}'))
                    else:
                        self.stdout.write(self.style.SUCCESS('✓ All required columns exist'))
                    
                    # Check if we have settings
                    cursor.execute('SELECT COUNT(*) FROM admin_panel_botsettings')
                    count = cursor.fetchone()[0]
                    
                    if count > 0:
                        self.stdout.write(self.style.SUCCESS(f'✓ Found {count} settings record(s)'))
                        
                        # Get BOT_TOKEN
                        token = os.environ.get('BOT_TOKEN')
                        if token:
                            self.stdout.write(f'Using BOT_TOKEN from environment: {token[:5]}...{token[-5:]}')
                            
                            if not check_only:
                                # Update token
                                cursor.execute("""
                                    UPDATE admin_panel_botsettings 
                                    SET bot_token = %s, bot_username = %s
                                    WHERE id = (SELECT MIN(id) FROM admin_panel_botsettings)
                                """, [token, 'Channels_hunt_bot'])
                                self.stdout.write(self.style.SUCCESS('✓ Updated bot token in database'))
                    else:
                        self.stdout.write(self.style.WARNING('No settings found'))
                        
                        if not check_only:
                            # Create settings
                            token = os.environ.get('BOT_TOKEN', '7923260865:AAGYew9JnOJV6hz0LGeRCb1kS6AejHoX61g')
                            cursor.execute("""
                                INSERT INTO admin_panel_botsettings (bot_token, bot_username, menu_style) 
                                VALUES (%s, %s, %s)
                            """, [token, 'Channels_hunt_bot', 'default'])
                            self.stdout.write(self.style.SUCCESS('✓ Created default settings'))
                else:
                    self.stdout.write(self.style.WARNING('BotSettings table does not exist'))
                    
                    if not check_only:
                        # Create table
                        self.stdout.write('Creating BotSettings table...')
                        cursor.execute("""
                            CREATE TABLE admin_panel_botsettings (
                                id SERIAL PRIMARY KEY,
                                bot_token VARCHAR(255) NOT NULL,
                                bot_username VARCHAR(255) NULL,
                                welcome_message TEXT NULL,
                                auth_guide_text TEXT NULL,
                                menu_style VARCHAR(50) NULL
                            )
                        """)
                        self.stdout.write(self.style.SUCCESS('✓ Created BotSettings table'))
                        
                        # Create default settings
                        token = os.environ.get('BOT_TOKEN', '7923260865:AAGYew9JnOJV6hz0LGeRCb1kS6AejHoX61g')
                        cursor.execute("""
                            INSERT INTO admin_panel_botsettings (bot_token, bot_username, menu_style) 
                            VALUES (%s, %s, %s)
                        """, [token, 'Channels_hunt_bot', 'default'])
                        self.stdout.write(self.style.SUCCESS('✓ Created default settings'))
                
                if not check_only:
                    connection.commit()
                    self.stdout.write(self.style.SUCCESS('✓ Changes committed to database'))
                else:
                    self.stdout.write(self.style.SUCCESS('✓ Check-only mode, no changes made'))
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'Database error: {e}'))
            if not check_only:
                try:
                    connection.rollback()
                    self.stdout.write(self.style.SUCCESS('✓ Changes rolled back'))
                except:
                    pass
        
        self.stdout.write(self.style.SUCCESS('=== Database Debug Completed ===')) 