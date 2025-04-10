#!/usr/bin/env python
"""
Fix for nested staticfiles directories causing Railway deployment to fail
"""
import os
import shutil
import sys
import glob

def fix_staticfiles():
    """Clean up nested staticfiles directories and fix settings"""
    print("Starting staticfiles directory cleanup...")
    
    # Get the current directory
    base_dir = os.path.dirname(os.path.abspath(__file__))
    
    # Check if staticfiles directory exists
    staticfiles_dir = os.path.join(base_dir, 'staticfiles')
    if os.path.exists(staticfiles_dir):
        print(f"Found staticfiles directory at {staticfiles_dir}")
        
        # Look for nested staticfiles directories
        nested_dirs = glob.glob(os.path.join(staticfiles_dir, '**/staticfiles'), recursive=True)
        print(f"Found {len(nested_dirs)} nested staticfiles directories")
        
        for nested_dir in nested_dirs:
            print(f"Removing nested directory: {nested_dir}")
            
            try:
                # If it's a symlink or file, use os.remove
                if os.path.islink(nested_dir) or os.path.isfile(nested_dir):
                    os.remove(nested_dir)
                # If it's a directory, use shutil.rmtree
                else:
                    shutil.rmtree(nested_dir)
                    
                print(f"Successfully removed {nested_dir}")
            except Exception as e:
                print(f"Error removing {nested_dir}: {str(e)}")
        
        # Completely remove and recreate the staticfiles directory to ensure a clean state
        try:
            print("Removing entire staticfiles directory...")
            shutil.rmtree(staticfiles_dir)
            print("Successfully removed staticfiles directory")
        except Exception as e:
            print(f"Error removing staticfiles directory: {str(e)}")
    else:
        print("No staticfiles directory found. Creating it...")
    
    # Create a clean staticfiles directory
    try:
        os.makedirs(staticfiles_dir, exist_ok=True)
        print("Created clean staticfiles directory")
    except Exception as e:
        print(f"Error creating staticfiles directory: {str(e)}")
    
    # Fix settings.py to ensure correct static files configuration
    try:
        from core.settings import STATIC_ROOT, STATICFILES_DIRS, BASE_DIR
        print(f"Current STATIC_ROOT: {STATIC_ROOT}")
        print(f"Current STATICFILES_DIRS: {STATICFILES_DIRS}")
        
        # Ensure STATIC_ROOT is correct
        if not STATIC_ROOT.endswith('staticfiles'):
            print("WARNING: STATIC_ROOT does not end with 'staticfiles'")
        
        # Ensure STATICFILES_DIRS does not include BASE_DIR
        if BASE_DIR in STATICFILES_DIRS:
            print("WARNING: BASE_DIR is in STATICFILES_DIRS, which may cause recursive collection")
        
        # Ensure STATICFILES_DIRS does not include STATIC_ROOT
        if STATIC_ROOT in STATICFILES_DIRS:
            print("WARNING: STATIC_ROOT is in STATICFILES_DIRS, which will cause recursive collection")
    except ImportError:
        print("Could not import settings. Skipping settings check.")
    
    print("Staticfiles cleanup complete.")
    return True

def update_settings():
    """Update settings.py to fix static files configuration"""
    settings_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'core', 'settings.py')
    
    if not os.path.exists(settings_path):
        print(f"Settings file not found at {settings_path}")
        return False
    
    print(f"Updating settings file at {settings_path}")
    
    with open(settings_path, 'r', encoding='utf-8') as file:
        settings_content = file.read()
    
    # Replace problematic STATICFILES_DIRS settings
    if 'STATICFILES_DIRS = [' in settings_content:
        # New configuration that avoids recursive collection
        new_dirs = """STATICFILES_DIRS = [
    os.path.join(BASE_DIR, 'static'),
    # Do not include the BASE_DIR itself - this was causing recursive collection
]"""
        # Find and replace the STATICFILES_DIRS configuration
        start_idx = settings_content.find('STATICFILES_DIRS = [')
        end_idx = settings_content.find(']', start_idx)
        if start_idx != -1 and end_idx != -1:
            end_idx += 1  # Include the closing bracket
            settings_content = settings_content[:start_idx] + new_dirs + settings_content[end_idx:]
            print("Updated STATICFILES_DIRS configuration")
    
    # Ensure STATIC_ROOT is correctly set
    if 'STATIC_ROOT =' in settings_content:
        new_root = "STATIC_ROOT = os.path.join(BASE_DIR, 'staticfiles')"
        # Find and replace the STATIC_ROOT configuration
        start_idx = settings_content.find('STATIC_ROOT =')
        end_idx = settings_content.find('\n', start_idx)
        if start_idx != -1 and end_idx != -1:
            settings_content = settings_content[:start_idx] + new_root + settings_content[end_idx:]
            print("Updated STATIC_ROOT configuration")
    
    # Write the updated settings back to the file
    with open(settings_path, 'w', encoding='utf-8') as file:
        file.write(settings_content)
    
    print("Settings file updated successfully")
    return True

def update_requirements():
    """Update requirements.txt to ensure aiogram is included"""
    requirements_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'requirements.txt')
    
    if not os.path.exists(requirements_path):
        print(f"Requirements file not found at {requirements_path}")
        return False
    
    print(f"Checking requirements file at {requirements_path}")
    
    with open(requirements_path, 'r', encoding='utf-8') as file:
        requirements_content = file.read()
    
    # Check if aiogram is already in requirements
    if 'aiogram' not in requirements_content:
        print("Adding aiogram to requirements.txt")
        with open(requirements_path, 'a', encoding='utf-8') as file:
            file.write('\naiogram>=3.0.0\n')
        print("Added aiogram to requirements.txt")
    else:
        print("aiogram is already in requirements.txt")
    
    return True

if __name__ == "__main__":
    print("Running static files fix script...")
    fix_staticfiles()
    update_settings()
    update_requirements()
    print("Fix script completed. Please redeploy the application.") 