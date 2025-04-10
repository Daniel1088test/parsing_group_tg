#!/usr/bin/env python
"""
Test script to render the categories_list.html template
"""
import os
import sys
import django
from django.template.loader import render_to_string
from django.template import TemplateDoesNotExist

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()

def test_render_template():
    """Test render the categories_list.html template"""
    from admin_panel.models import Category
    from django.template.loader import get_template
    
    print("Getting categories from database...")
    categories = list(Category.objects.all())
    print(f"Found {len(categories)} categories")
    
    print("\nTrying to render template...")
    try:
        template = get_template('admin_panel/categories_list.html')
        print(f"Template found: {template.origin.name}")
        
        # Create a context similar to what the view would create
        context = {
            'categories': categories,
        }
        
        # Try to render the template
        rendered = template.render(context)
        
        # If we get here, it worked
        print("\nTemplate rendered successfully!")
        
        # Write the rendered output to a file for inspection
        with open('rendered_output.html', 'w', encoding='utf-8') as f:
            f.write(rendered)
        
        print(f"Rendered output saved to: {os.path.abspath('rendered_output.html')}")
        
    except TemplateDoesNotExist as e:
        print(f"Template not found error: {e}")
    except Exception as e:
        import traceback
        print(f"Error rendering template: {e}")
        print(traceback.format_exc())

if __name__ == "__main__":
    test_render_template() 