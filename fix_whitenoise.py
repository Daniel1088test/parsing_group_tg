#!/usr/bin/env python
"""
Fix for whitenoise storage issues causing Railway deployment failure
This script updates the storage class in settings.py to use a simpler
storage class that doesn't rely on file manifests.
"""
import os
import sys
import re

def update_settings():
    """Update settings.py to use a simpler storage class"""
    settings_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'core', 'settings.py')
    
    if not os.path.exists(settings_path):
        print(f"Settings file not found at {settings_path}")
        return False
    
    print(f"Updating settings file at {settings_path}")
    
    with open(settings_path, 'r', encoding='utf-8') as file:
        settings_content = file.read()
    
    # Find the current STATICFILES_STORAGE setting
    storage_pattern = r"STATICFILES_STORAGE\s*=\s*['\"](.*)['\"]"
    current_storage = re.search(storage_pattern, settings_content)
    
    if current_storage:
        current_storage_class = current_storage.group(1)
        print(f"Current storage class: {current_storage_class}")
        
        # If using CompressedManifestStaticFilesStorage, change to SimpleStorage
        if 'CompressedManifestStaticFilesStorage' in current_storage_class:
            print("Replacing CompressedManifestStaticFilesStorage with WhiteNoiseStaticFilesStorage")
            new_settings_content = re.sub(
                storage_pattern,
                "STATICFILES_STORAGE = 'whitenoise.storage.WhiteNoiseStaticFilesStorage'",
                settings_content
            )
            
            # Write the updated content back to the file
            with open(settings_path, 'w', encoding='utf-8') as file:
                file.write(new_settings_content)
            
            print("Storage class updated successfully")
            return True
        else:
            print(f"Already using a different storage class: {current_storage_class}. No changes made.")
    else:
        print("STATICFILES_STORAGE setting not found. No changes made.")
    
    return False

if __name__ == "__main__":
    print("Running whitenoise storage fix script...")
    if update_settings():
        print("Successfully updated whitenoise storage settings")
    else:
        print("No updates were needed or settings could not be updated")
    print("Fix script completed.") 