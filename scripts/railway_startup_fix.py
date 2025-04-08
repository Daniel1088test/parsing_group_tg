#!/usr/bin/env python3
import os
import sys
import logging
import subprocess
import importlib
import time

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(levelname)s %(asctime)s %(name)s %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S',
)
logger = logging.getLogger('railway_startup_fix')

def clean_pyc_files():
    """Remove all .pyc files to ensure clean imports"""
    logger.info("Cleaning Python cache files")
    
    root_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    count = 0
    
    for dirpath, dirnames, filenames in os.walk(root_dir):
        for filename in filenames:
            if filename.endswith('.pyc') or filename.endswith('.pyo'):
                filepath = os.path.join(dirpath, filename)
                try:
                    os.remove(filepath)
                    count += 1
                except Exception as e:
                    logger.error(f"Error removing {filepath}: {e}")
    
    # Also clean __pycache__ directories
    for dirpath, dirnames, filenames in os.walk(root_dir):
        for dirname in list(dirnames):  # Use list to make a copy since we're modifying
            if dirname == '__pycache__':
                try:
                    cache_dir = os.path.join(dirpath, dirname)
                    for f in os.listdir(cache_dir):
                        try:
                            os.remove(os.path.join(cache_dir, f))
                        except:
                            pass
                    try:
                        os.rmdir(cache_dir)
                    except:
                        pass
                    dirnames.remove(dirname)  # Don't descend into directories we've deleted
                except Exception as e:
                    logger.error(f"Error cleaning __pycache__: {e}")
    
    logger.info(f"Removed {count} cache files")
    return count

def ensure_view_function():
    """Make sure the run_migrations_view function is in views.py"""
    views_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 
                             'admin_panel', 'views.py')
    
    if not os.path.exists(views_path):
        logger.error(f"views.py not found at {views_path}")
        return False
    
    with open(views_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    if 'def run_migrations_view' in content:
        logger.info("run_migrations_view function found, no need to add it")
        return True
    
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
    
    try:
        with open(views_path, 'a', encoding='utf-8') as f:
            f.write(view_function)
        logger.info("Added run_migrations_view function to views.py")
        return True
    except Exception as e:
        logger.error(f"Error adding function: {e}")
        return False

def check_urls_file():
    """Verify that the URL pattern for run_migrations exists"""
    urls_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 
                            'admin_panel', 'urls.py')
    
    if not os.path.exists(urls_path):
        logger.error(f"urls.py not found at {urls_path}")
        return False
    
    with open(urls_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    if "path('run-migrations/', views.run_migrations_view" in content:
        logger.info("run-migrations URL pattern found")
        return True
    
    logger.error("run-migrations URL pattern not found in urls.py")
    return False

def run_migrations():
    """Run Django migrations"""
    logger.info("Running database migrations")
    
    # First try to fix migration dependencies
    try:
        from scripts.fix_migrations_dependency import fix_migration_dependencies, create_fake_migrations
        logger.info("Fixing migration dependencies...")
        fixed = fix_migration_dependencies()
        if not fixed:
            logger.info("Creating placeholder migrations...")
            create_fake_migrations()
    except Exception as e:
        logger.error(f"Error fixing migration dependencies: {e}")
    
    # Now try to run migrations
    result = subprocess.run(
        ["python", "manage.py", "migrate", "--noinput"],
        capture_output=True,
        text=True
    )
    
    if result.returncode == 0:
        logger.info("Migrations applied successfully")
        logger.info(result.stdout)
        return True
    else:
        logger.error(f"Migration failed: {result.stderr}")
        
        # Fallback: try to run migrations with --fake-initial
        logger.info("Trying with --fake-initial...")
        result = subprocess.run(
            ["python", "manage.py", "migrate", "--noinput", "--fake-initial"],
            capture_output=True,
            text=True
        )
        
        if result.returncode == 0:
            logger.info("Migrations applied with --fake-initial")
            return True
        else:
            logger.error(f"Migration with --fake-initial failed: {result.stderr}")
            
            # Fallback: try individual apps one by one
            logger.info("Trying to migrate apps individually...")
            apps = ["admin", "auth", "contenttypes", "sessions", "admin_panel"]
            for app in apps:
                try:
                    subprocess.run(
                        ["python", "manage.py", "migrate", app, "--noinput"],
                        capture_output=True,
                        check=False
                    )
                    logger.info(f"Attempted migration for {app}")
                except Exception:
                    pass
            
            return False

def run_server_check():
    """Run Django check to validate the setup"""
    logger.info("Running Django check")
    
    result = subprocess.run(
        ["python", "manage.py", "check"],
        capture_output=True,
        text=True
    )
    
    if result.returncode == 0:
        logger.info("Django check passed")
        return True
    else:
        logger.error(f"Django check failed: {result.stderr}")
        return False

if __name__ == "__main__":
    logger.info("Starting Railway startup fix script")
    
    # Clean Python bytecode files
    clean_pyc_files()
    
    # Make sure the view function exists
    ensure_view_function()
    
    # Check that URL patterns are correct
    check_urls_file()
    
    # Run migrations if needed
    run_migrations()
    
    # Run Django check
    run_server_check()
    
    logger.info("Railway startup fix completed") 