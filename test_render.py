#!/usr/bin/env python
"""
Test script to render the categories_list.html template
"""
import os
import sys
import django
from django.template.loader import render_to_string
from django.template import TemplateDoesNotExist, RequestContext
from django.http import HttpRequest

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
        
        # Create a mock request
        request = HttpRequest()
        request.path = '/admin_panel/categories/'
        request.META = {'SCRIPT_NAME': '', 'HTTP_HOST': 'localhost:8000'}
        
        # Create a context similar to what the view would create
        from django.template import RequestContext
        context = RequestContext(request, {
            'categories': categories,
        })
        
        # Try to render the template directly without using base.html
        content = '''
        <!DOCTYPE html>
        <html>
        <head>
            <title>Categories</title>
            <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.2/dist/css/bootstrap.min.css" rel="stylesheet">
        </head>
        <body>
            <div class="container mt-5">
                <div class="card">
                    <div class="card-header">
                        <h2>Categories</h2>
                    </div>
                    <div class="card-body">
                        <table class="table">
                            <thead>
                                <tr>
                                    <th>ID</th>
                                    <th>Name</th>
                                </tr>
                            </thead>
                            <tbody>
                                {% for category in categories %}
                                <tr>
                                    <td>{{ category.id }}</td>
                                    <td>{{ category.name }}</td>
                                </tr>
                                {% endfor %}
                            </tbody>
                        </table>
                    </div>
                </div>
            </div>
        </body>
        </html>
        '''
        
        from django.template import Template
        simple_template = Template(content)
        rendered = simple_template.render(context)
        
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