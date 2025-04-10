#!/usr/bin/env python
"""
Debug script to check template loading in Django
"""
import os
import sys
import django
from django.template.loader import get_template
from django.template import TemplateDoesNotExist
from django.conf import settings

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()

def check_template(template_name):
    """Check if a template can be found and loaded"""
    print(f"\nChecking template: {template_name}")
    
    # Print template directories
    print("\nTemplate directories:")
    for engine in settings.TEMPLATES:
        for directory in engine.get('DIRS', []):
            print(f"- {directory} (exists: {os.path.exists(directory)})")
    
    # Check if APP_DIRS is enabled
    print("\nAPP_DIRS enabled?")
    for engine in settings.TEMPLATES:
        print(f"- {engine.get('APP_DIRS', False)}")
    
    # List installed apps
    print("\nInstalled apps that might contain templates:")
    for app in settings.INSTALLED_APPS:
        app_path = app.replace('.', '/')
        template_dir = os.path.join(settings.BASE_DIR, app_path, 'templates')
        print(f"- {app} (template dir exists: {os.path.exists(template_dir)})")
    
    # Try to find the template
    try:
        template = get_template(template_name)
        print(f"\nTemplate '{template_name}' FOUND! Source: {template.origin.name}")
    except TemplateDoesNotExist:
        print(f"\nTemplate '{template_name}' NOT FOUND!")
        
        # Check if it exists in any of the expected locations
        for engine in settings.TEMPLATES:
            for directory in engine.get('DIRS', []):
                template_path = os.path.join(directory, template_name)
                if os.path.exists(template_path):
                    print(f"- EXISTS at {template_path}, but wasn't found by Django")
                else:
                    print(f"- Doesn't exist at {template_path}")

if __name__ == "__main__":
    template_to_check = "admin_panel/categories_list.html"
    if len(sys.argv) > 1:
        template_to_check = sys.argv[1]
    
    check_template(template_to_check) 