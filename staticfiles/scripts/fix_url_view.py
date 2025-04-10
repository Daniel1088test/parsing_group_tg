#!/usr/bin/env python3
import os
import sys
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(levelname)s %(asctime)s %(name)s %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S',
)
logger = logging.getLogger('fix_url_view')

def fix_migration_view():
    """Ensures the run_migrations_view exists in views.py"""
    
    # First check if the view function already exists
    views_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 
                             'admin_panel', 'views.py')
    
    if not os.path.exists(views_path):
        logger.error(f"views.py file not found at {views_path}")
        return False
        
    # Check if the function is already defined
    with open(views_path, 'r', encoding='utf-8') as f:
        content = f.read()
        
    if 'def run_migrations_view' in content:
        logger.info("run_migrations_view function already exists in views.py")
        return True
        
    # Function not found, add it
    logger.info("Adding run_migrations_view function to views.py")
    
    view_function = '''
@login_required
def run_migrations_view(request):
    """View for running database migrations"""
    if request.method == 'POST':
        try:
            # Import and run the migration script
            from scripts.run_migrations import run_migrations
            success = run_migrations()
            
            if success:
                messages.success(request, "Database migrations have been applied successfully.")
            else:
                messages.error(request, "Failed to apply migrations. Please check the logs.")
        except Exception as e:
            messages.error(request, f"Error running migrations: {str(e)}")
    
    return render(request, 'admin_panel/run_migrations.html')
'''
    
    # Add the function to the end of the file
    with open(views_path, 'a', encoding='utf-8') as f:
        f.write(view_function)
        
    logger.info("Successfully added run_migrations_view function to views.py")
    return True

if __name__ == "__main__":
    logger.info("Starting URL view fix script")
    
    if fix_migration_view():
        logger.info("Fix completed successfully")
        sys.exit(0)
    else:
        logger.error("Fix failed")
        sys.exit(1) 