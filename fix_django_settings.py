#!/usr/bin/env python
"""
Script to fix Django settings issues for Railway deployment
"""
import os
import sys
import logging
import re
import importlib

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger("fix_django_settings")

def install_package(package):
    """Install a package using pip"""
    logger.info(f"Installing missing package: {package}")
    import subprocess
    try:
        subprocess.check_call([sys.executable, "-m", "pip", "install", package])
        logger.info(f"Successfully installed {package}")
        return True
    except subprocess.CalledProcessError as e:
        logger.error(f"Failed to install {package}: {e}")
        return False

def import_or_install(module_name, package_name=None):
    """Import a module or install it if missing"""
    if package_name is None:
        package_name = module_name
        
    try:
        return importlib.import_module(module_name)
    except ImportError:
        logger.warning(f"Module {module_name} not found, attempting to install {package_name}")
        if install_package(package_name):
            try:
                return importlib.import_module(module_name)
            except ImportError as e:
                logger.error(f"Still cannot import {module_name} after installing: {e}")
        return None

def fix_settings_file(settings_path='core/settings.py'):
    """Fix Django settings file by patching it if needed"""
    logger.info(f"Checking Django settings file: {settings_path}")
    
    if not os.path.exists(settings_path):
        logger.error(f"Settings file not found: {settings_path}")
        return False
    
    with open(settings_path, 'r') as f:
        content = f.read()
    
    changes_made = False
    
    # Check for dj_database_url import
    if "import dj_database_url" in content and not import_or_install("dj_database_url", "dj-database-url"):
        # Add fallback if the module cannot be imported
        new_content = re.sub(
            r'import dj_database_url',
            'try:\n    import dj_database_url\nexcept ImportError:\n    print("dj_database_url module not available, using fallback settings")\n    dj_database_url = None',
            content
        )
        if new_content != content:
            content = new_content
            changes_made = True
    
    # Check for DATABASE_URL usage without fallback
    if "dj_database_url.parse" in content:
        new_content = re.sub(
            r'DATABASES\s*=\s*{[^}]*\'default\'\s*:\s*dj_database_url\.parse\([^)]+\)[^}]*}',
            """DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': os.path.join(BASE_DIR, 'db.sqlite3'),
    }
}

# Try to use DATABASE_URL if available
if 'DATABASE_URL' in os.environ:
    try:
        import dj_database_url
        DATABASES['default'] = dj_database_url.parse(os.environ.get('DATABASE_URL'))
    except (ImportError, Exception) as e:
        print(f"Error setting up database from URL: {e}")""",
            content
        )
        if new_content != content:
            content = new_content
            changes_made = True
    
    # Check for whitenoise
    if "whitenoise" in content and not import_or_install("whitenoise"):
        # Make whitenoise optional
        new_content = re.sub(
            r'\'whitenoise\.middleware\.WhiteNoiseMiddleware\',',
            """# Optional whitenoise middleware
    'whitenoise.middleware.WhiteNoiseMiddleware' if 'whitenoise' in sys.modules else '',""",
            content
        )
        if new_content != content:
            content = new_content
            changes_made = True
    
    # Write changes back to file
    if changes_made:
        logger.info(f"Making changes to {settings_path}")
        with open(settings_path, 'w') as f:
            f.write(content)
        return True
    else:
        logger.info(f"No changes needed for {settings_path}")
        return False

def ensure_static_files():
    """Ensure static files directories exist"""
    for directory in ['static', 'staticfiles', 'media']:
        os.makedirs(directory, exist_ok=True)
        logger.info(f"Ensured directory exists: {directory}")
    
    # Create basic health check files
    for filename in ['health.txt', 'healthz.txt', 'health.html', 'healthz.html']:
        for directory in ['', 'static/', 'staticfiles/']:
            with open(f"{directory}{filename}", 'w') as f:
                f.write("OK")

def main():
    """Main function"""
    logger.info("Starting Django settings fix")
    
    # Install required packages
    for package in ["dj-database-url", "whitenoise", "python-dotenv"]:
        try:
            import_or_install(package.replace("-", "_"), package)
        except Exception as e:
            logger.error(f"Error installing {package}: {e}")
    
    # Fix settings file
    try:
        fix_settings_file()
    except Exception as e:
        logger.error(f"Error fixing settings: {e}")
    
    # Ensure static files
    try:
        ensure_static_files()
    except Exception as e:
        logger.error(f"Error ensuring static files: {e}")
    
    logger.info("Django settings fix completed")
    return True

if __name__ == "__main__":
    try:
        main()
        sys.exit(0)
    except Exception as e:
        logger.error(f"Unhandled error: {e}")
        sys.exit(1) 