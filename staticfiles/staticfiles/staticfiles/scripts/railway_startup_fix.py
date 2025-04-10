#!/usr/bin/env python
"""
Script to fix Django setup issues on Railway deployment
"""
import os
import sys
import glob
import re
import logging
import subprocess
from pathlib import Path

# Add the parent directory to the Python path
parent_dir = str(Path(__file__).resolve().parent.parent)
sys.path.append(parent_dir)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s %(name)s %(levelname)s %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S',
)
logger = logging.getLogger('railway_startup_fix')

def clean_cache_files():
    """Clean Python cache files to avoid import issues"""
    logger.info("Cleaning Python cache files")
    
    # Find and remove .pyc files and __pycache__ directories
    pyc_files = glob.glob(f"{parent_dir}/**/*.pyc", recursive=True)
    for pyc_file in pyc_files:
        try:
            os.remove(pyc_file)
        except Exception as e:
            logger.error(f"Error removing {pyc_file}: {e}")
    
    pycache_dirs = glob.glob(f"{parent_dir}/**/__pycache__", recursive=True)
    for pycache_dir in pycache_dirs:
        try:
            for cached_file in os.listdir(pycache_dir):
                os.remove(os.path.join(pycache_dir, cached_file))
            os.rmdir(pycache_dir)
        except Exception as e:
            logger.error(f"Error removing {pycache_dir}: {e}")
    
    logger.info(f"Removed {len(pyc_files)} cache files")
    return len(pyc_files)

def fix_views_file():
    """Add run_migrations_view to views.py if it doesn't exist"""
    views_path = os.path.join(parent_dir, 'admin_panel', 'views.py')
    
    if not os.path.exists(views_path):
        logger.error(f"Views file not found at {views_path}")
        return False
    
    # Check if run_migrations_view function already exists
    with open(views_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    if 'def run_migrations_view' in content:
        logger.info("run_migrations_view function found, no need to add it")
        return True
    
    # Add the function to the end of the file
    with open(views_path, 'a', encoding='utf-8') as f:
        f.write("""
@login_required
def run_migrations_view(request):
    \"\"\"View for running database migrations\"\"\"
    if request.method == 'POST':
        try:
            # Run migrations
            from django.core.management import call_command
            call_command('migrate')
            messages.success(request, "Database migrations have been applied successfully.")
        except Exception as e:
            messages.error(request, f"Error running migrations: {str(e)}")
    
    return render(request, 'admin_panel/run_migrations.html')
""")
    
    logger.info("Added run_migrations_view function to views.py")
    return True

def fix_urls_file():
    """Add run-migrations URL pattern to urls.py if it doesn't exist"""
    urls_path = os.path.join(parent_dir, 'admin_panel', 'urls.py')
    
    if not os.path.exists(urls_path):
        logger.error(f"URLs file not found at {urls_path}")
        return False
    
    # Check if run-migrations URL already exists
    with open(urls_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    if "path('run-migrations/" in content or 'path("run-migrations/' in content:
        logger.info("run-migrations URL pattern found")
        return True
    
    # Import the view if it's not already imported
    if 'from .views import run_migrations_view' not in content and 'import run_migrations_view' not in content:
        # Add import at the beginning after other imports
        import_pattern = r'(from .views import .*?\n)'
        import_match = re.search(import_pattern, content)
        
        if import_match:
            # Add to existing import
            last_import = import_match.group(1)
            new_import = last_import.rstrip('\n') + ', run_migrations_view\n'
            content = content.replace(last_import, new_import)
        else:
            # Add new import line after the last import
            content = re.sub(r'(from .* import .*?\n)', r'\1from .views import run_migrations_view\n', content, count=1)
    
    # Add URL pattern
    urlpatterns_match = re.search(r'urlpatterns\s*=\s*\[(.*?)\]', content, re.DOTALL)
    if urlpatterns_match:
        urlpatterns_content = urlpatterns_match.group(1)
        
        # Add new URL pattern
        new_urlpatterns = urlpatterns_content.rstrip() + ",\n    path('run-migrations/', run_migrations_view, name='run_migrations'),\n"
        content = content.replace(urlpatterns_content, new_urlpatterns)
        
        # Write the modified content back to the file
        with open(urls_path, 'w', encoding='utf-8') as f:
            f.write(content)
        
        logger.info("Added run-migrations URL pattern to urls.py")
        return True
    else:
        logger.error("Could not find urlpatterns in urls.py")
        return False

def run_migrations():
    """Run database migrations"""
    logger.info("Running database migrations")
    
    try:
        # Try to run fix_migrations_dependency.py script
        migration_script = os.path.join(parent_dir, 'scripts', 'fix_migrations_dependency.py')
        if os.path.exists(migration_script):
            try:
                # Make sure it's executable
                os.chmod(migration_script, 0o755)
                
                # Run the script as a Python module to ensure imports work
                subprocess.run([sys.executable, migration_script], check=True)
                logger.info("Fixed migration dependencies successfully")
            except Exception as e:
                logger.error(f"Error fixing migration dependencies: {e}")
        
        # Set up Django
        sys.path.insert(0, parent_dir)
        os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
        
        # Directly import Django
        import django
        from django.core.management import call_command
        
        django.setup()
        
        # Run migrations
        call_command('migrate')
        logger.info("Migrations applied successfully")
        return True
    except Exception as e:
        logger.error(f"Error running migrations: {e}")
        return False

def run_django_check():
    """Run Django system check to verify setup"""
    logger.info("Running Django check")
    
    try:
        sys.path.insert(0, parent_dir)
        os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
        
        import django
        from django.core.management import call_command
        
        django.setup()
        
        # Run system check
        call_command('check')
        logger.info("Django check passed")
        return True
    except Exception as e:
        logger.error(f"Error running Django check: {e}")
        return False

def main():
    """Main function to run all fixes"""
    logger.info("Starting Railway startup fix script")
    
    # Clean cache files
    clean_cache_files()
    
    # Fix views and URLs
    fix_views_file()
    fix_urls_file()
    
    # Run database migrations
    run_migrations()
    
    # Run Django system check
    run_django_check()
    
    logger.info("Railway startup fix completed")

if __name__ == "__main__":
    main() 