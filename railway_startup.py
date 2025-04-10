#!/usr/bin/env python
"""
Script for deploying on Railway platform.
Runs migrations, collects static files, and starts the Django application.
"""
import os
import sys
import logging
import subprocess
import time
import traceback

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler(sys.stdout)]
)

logger = logging.getLogger('railway_startup')

def run_command(command, check=True, shell=False, env=None):
    """Run a command and return its output"""
    logger.info(f"Running command: {command}")
    if isinstance(command, str) and not shell:
        command = command.split()
    
    try:
        result = subprocess.run(
            command,
            check=check,
            shell=shell,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            env=env
        )
        logger.info(f"Command output: {result.stdout}")
        if result.stderr:
            logger.warning(f"Command stderr: {result.stderr}")
        return result
    except subprocess.CalledProcessError as e:
        logger.error(f"Command failed: {e}")
        logger.error(f"Command stderr: {e.stderr}")
        if not check:
            return e
        raise
    except Exception as e:
        logger.error(f"Error running command: {e}")
        logger.error(traceback.format_exc())
        if not check:
            return None
        raise

def run_fix_scripts():
    """Run scripts to fix deployments issues"""
    # Run fix_static_files.py to fix nested staticfiles
    if os.path.exists("fix_static_files.py"):
        logger.info("Running fix_static_files.py...")
        run_command([sys.executable, "fix_static_files.py"], check=False)
    else:
        logger.warning("fix_static_files.py not found. Create this file to fix static files issues.")
    
    # Run fix_whitenoise.py to fix storage issues
    if os.path.exists("fix_whitenoise.py"):
        logger.info("Running fix_whitenoise.py...")
        run_command([sys.executable, "fix_whitenoise.py"], check=False)
    else:
        logger.warning("fix_whitenoise.py not found. Create this file to fix whitenoise storage issues.")
    
    # Run fix_migration_conflict.py if it exists
    if os.path.exists("fix_migration_conflict.py"):
        logger.info("Running fix_migration_conflict.py...")
        run_command([sys.executable, "fix_migration_conflict.py"], check=False)
    
    # Add additional fix scripts here

def apply_database_fixes():
    """Apply fixes to the database if needed"""
    try:
        # Check if any migrations need to be applied first
        run_command(["python", "manage.py", "showmigrations"], check=False)
        
        # Run migrations
        run_command(["python", "manage.py", "migrate"], check=False)
        
        # Fix permissions
        run_command(["python", "manage.py", "fix_permissions"], check=False)
    except Exception as e:
        logger.error(f"Error applying database fixes: {e}")
        logger.error(traceback.format_exc())

def run_migrations():
    """Run database migrations"""
    try:
        logger.info("Running migrations...")
        run_command(["python", "manage.py", "migrate", "--noinput"])
        logger.info("Migrations completed successfully")
    except Exception as e:
        logger.error(f"Error running migrations: {e}")
        logger.error(traceback.format_exc())
        # Don't exit, try to continue with the deployment

def collect_static_files():
    """Collect static files"""
    try:
        logger.info("Collecting static files...")
        run_command(["python", "manage.py", "collectstatic", "--noinput", "--clear"])
        logger.info("Static files collected successfully")
    except Exception as e:
        logger.error(f"Error collecting static files: {e}")
        logger.error(traceback.format_exc())
        # Don't exit, try to continue with the deployment

def ensure_templates_setup():
    """Ensure templates are correctly set up"""
    try:
        template_dir = os.path.join(os.getcwd(), "templates")
        if not os.path.exists(template_dir):
            logger.info("Creating templates directory...")
            os.makedirs(template_dir, exist_ok=True)
        
        admin_panel_dir = os.path.join(template_dir, "admin_panel")
        if not os.path.exists(admin_panel_dir):
            logger.info("Creating admin_panel template directory...")
            os.makedirs(admin_panel_dir, exist_ok=True)
        
        # Check if we have necessary index templates
        index_template = os.path.join(admin_panel_dir, "index.html")
        if not os.path.exists(index_template):
            logger.warning(f"Template not found: {index_template}")
    except Exception as e:
        logger.error(f"Error setting up templates: {e}")
        logger.error(traceback.format_exc())

def start_bot_and_parser():
    """Start the bot and parser"""
    try:
        logger.info("Starting the bot and parser in background...")
        env = os.environ.copy()
        env["PYTHONUNBUFFERED"] = "1"  # Ensure Python output is unbuffered
        
        # Run the bot in the background
        subprocess.Popen(
            ["python", "run.py"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            env=env
        )
        logger.info("Bot and parser started in background")
    except Exception as e:
        logger.error(f"Error starting bot and parser: {e}")
        logger.error(traceback.format_exc())

def main():
    """Main function to orchestrate the startup process"""
    logger.info("Starting Railway deployment process...")
    
    # Run fix scripts first
    run_fix_scripts()
    
    # Apply database fixes
    apply_database_fixes()
    
    # Run migrations
    run_migrations()
    
    # Collect static files
    collect_static_files()
    
    # Ensure templates are set up
    ensure_templates_setup()
    
    # Start the bot and parser
    start_bot_and_parser()
    
    # Get the port from environment variable
    port = os.environ.get("PORT", "8000")
    
    # Start the Django server
    logger.info(f"Starting Django server on port {port}...")
    
    # Use exec to replace the current process with the Django server
    os.execvp("gunicorn", ["gunicorn", f"--bind=0.0.0.0:{port}", "core.wsgi:application"])

if __name__ == "__main__":
    main() 