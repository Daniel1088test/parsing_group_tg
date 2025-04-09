#!/usr/bin/env python
import os
import sys
import django

# Setup Django
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()

from django.db import connection
import logging

logger = logging.getLogger(__name__)

def add_safe_session_method():
    """Add a method to the TelegramSession model manager to use a limited set of fields"""
    try:
        from admin_panel.models import TelegramSession, TelegramSessionManager
        
        # Define a safe method that only selects essential fields
        def get_safe_queryset(self):
            """Get a queryset with only essential fields to avoid schema issues"""
            return super(TelegramSessionManager, self).get_queryset().only(
                'id', 'phone', 'is_active', 'session_file', 'created_at', 'updated_at'
            )
        
        # Add the method to the manager
        TelegramSessionManager.get_queryset = get_safe_queryset
        print("✓ Added safe queryset method to TelegramSessionManager")
    except Exception as e:
        print(f"✕ Error adding safe queryset method: {e}")

def create_safe_views():
    """Create database views with only essential columns"""
    try:
        with connection.cursor() as cursor:
            # Create a safe view for TelegramSession
            cursor.execute("""
                CREATE VIEW IF NOT EXISTS safe_telegram_session AS
                SELECT id, phone, is_active, session_file, created_at, updated_at
                FROM admin_panel_telegramsession
            """)
            print("✓ Created safe_telegram_session view")
    except Exception as e:
        print(f"✕ Error creating safe view: {e}")

def update_models_module():
    """Update the models.py file to use safer access methods"""
    try:
        # First, ensure the backup exists
        models_file = 'admin_panel/models.py'
        backup_file = 'admin_panel/models.py.bak'
        
        if not os.path.exists(backup_file):
            import shutil
            shutil.copy2(models_file, backup_file)
            print(f"✓ Created backup of {models_file} -> {backup_file}")
        
        # Path to the models.py file
        admin_panel_models = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'admin_panel', 'models.py')
        
        # Read the current file
        with open(admin_panel_models, 'r', encoding='utf-8') as f:
            lines = f.readlines()
        
        # Update the TelegramSessionManager
        updated_lines = []
        in_manager_class = False
        manager_updated = False
        
        for line in lines:
            if 'class TelegramSessionManager' in line:
                in_manager_class = True
            
            if in_manager_class and 'def get_queryset' in line:
                # Replace the existing get_queryset method
                updated_lines.append('    def get_queryset(self):\n')
                updated_lines.append('        """Safe manager for TelegramSession that handles missing columns"""\n')
                updated_lines.append('        qs = super().get_queryset().only(\n')
                updated_lines.append('            "id", "phone", "is_active", "session_file", "created_at", "updated_at"\n')
                updated_lines.append('        )\n')
                updated_lines.append('        return qs\n')
                in_manager_class = False
                manager_updated = True
                continue
            
            if in_manager_class and 'return qs' in line:
                # We're at the end of the existing method
                in_manager_class = False
                continue
            
            if not in_manager_class or not manager_updated:
                updated_lines.append(line)
        
        # Write the updated file
        with open(admin_panel_models, 'w', encoding='utf-8') as f:
            f.writelines(updated_lines)
        
        print(f"✓ Updated {models_file} with safer queryset method")
    except Exception as e:
        print(f"✕ Error updating models.py: {e}")

if __name__ == "__main__":
    print("Applying emergency fixes to handle database schema issues...")
    
    # Add method to the model manager
    add_safe_session_method()
    
    # Create safe database views
    create_safe_views()
    
    # Update the models.py file
    update_models_module()
    
    print("\nEmergency fixes applied. Please restart your application.") 