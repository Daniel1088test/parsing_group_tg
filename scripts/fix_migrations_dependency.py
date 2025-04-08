#!/usr/bin/env python3
import os
import sys
import glob
import re
import logging
from pathlib import Path

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(levelname)s %(asctime)s %(name)s %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S',
)
logger = logging.getLogger('fix_migrations')

def find_migrations_directory():
    """Find the Django migrations directory"""
    # Try common paths
    possible_paths = [
        'admin_panel/migrations',
        'app/admin_panel/migrations',
        '../admin_panel/migrations',
    ]
    
    for path in possible_paths:
        if os.path.isdir(path):
            return path
    
    # If not found, search from current directory
    for root, dirs, files in os.walk('.'):
        if 'migrations' in dirs and '__init__.py' in [f for f in os.listdir(os.path.join(root, 'migrations'))]:
            return os.path.join(root, 'migrations')
    
    return None

def get_existing_migrations(migrations_dir):
    """Get a list of existing migration names in the directory"""
    migration_files = glob.glob(os.path.join(migrations_dir, '*.py'))
    
    # Extract the migration names (without .py extension)
    migration_names = []
    for file_path in migration_files:
        file_name = os.path.basename(file_path)
        if file_name != '__init__.py' and not file_name.startswith('__'):
            migration_name = os.path.splitext(file_name)[0]
            migration_names.append(migration_name)
    
    return migration_names

def fix_migration_dependencies():
    """Fix any broken migration dependencies"""
    migrations_dir = find_migrations_directory()
    if not migrations_dir:
        logger.error("Could not find migrations directory")
        return False
    
    logger.info(f"Found migrations directory at {migrations_dir}")
    
    # Get list of existing migrations
    existing_migrations = get_existing_migrations(migrations_dir)
    logger.info(f"Found {len(existing_migrations)} migration files")
    
    # Check each migration file for dependencies
    fixed_count = 0
    for migration_name in existing_migrations:
        migration_path = os.path.join(migrations_dir, f"{migration_name}.py")
        
        try:
            with open(migration_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Look for dependencies using regex
            dependency_pattern = r"dependencies\s*=\s*\[(.*?)\]"
            dependencies_match = re.search(dependency_pattern, content, re.DOTALL)
            
            if dependencies_match:
                dependencies_text = dependencies_match.group(1)
                
                # Check for non-existent dependencies
                app_migration_pattern = r"\('(\w+)',\s*'([^']+)'\)"
                for app_name, migration_name in re.findall(app_migration_pattern, dependencies_text):
                    dependency_exists = False
                    
                    # Check if the dependency exists in our list
                    if migration_name in existing_migrations:
                        dependency_exists = True
                    
                    # If dependency doesn't exist, fix it
                    if not dependency_exists:
                        logger.warning(f"Found broken dependency in {migration_path}: {app_name}.{migration_name}")
                        
                        # Find a suitable replacement (usually the earliest migration)
                        suitable_migrations = sorted([m for m in existing_migrations if m.startswith('0')])
                        if suitable_migrations:
                            replacement = suitable_migrations[0]
                            logger.info(f"Replacing with {app_name}.{replacement}")
                            
                            # Replace the dependency
                            new_dependency = f"('{app_name}', '{replacement}')"
                            old_dependency = f"('{app_name}', '{migration_name}')"
                            new_content = content.replace(old_dependency, new_dependency)
                            
                            # Write back to file
                            with open(migration_path, 'w', encoding='utf-8') as f:
                                f.write(new_content)
                            
                            fixed_count += 1
                            logger.info(f"Fixed dependency in {migration_path}")
        except Exception as e:
            logger.error(f"Error processing {migration_path}: {e}")
    
    logger.info(f"Fixed {fixed_count} migration dependencies")
    return fixed_count > 0

def create_fake_migrations():
    """Create fake migrations for missing dependencies"""
    migrations_dir = find_migrations_directory()
    if not migrations_dir:
        logger.error("Could not find migrations directory")
        return False
    
    # Check for any missing migrations referenced in migration files
    missing_migrations = set()
    existing_migrations = get_existing_migrations(migrations_dir)
    
    for migration_name in existing_migrations:
        migration_path = os.path.join(migrations_dir, f"{migration_name}.py")
        
        try:
            with open(migration_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Look for dependencies
            app_migration_pattern = r"\('(\w+)',\s*'([^']+)'\)"
            for app_name, dependency_name in re.findall(app_migration_pattern, content):
                if app_name == 'admin_panel' and dependency_name not in existing_migrations and dependency_name != 'initial':
                    missing_migrations.add(dependency_name)
        except Exception as e:
            logger.error(f"Error checking dependencies in {migration_path}: {e}")
    
    # Create fake migrations for missing dependencies
    created_count = 0
    for missing in missing_migrations:
        fake_migration_path = os.path.join(migrations_dir, f"{missing}.py")
        
        if not os.path.exists(fake_migration_path):
            logger.info(f"Creating fake migration for {missing}")
            
            # Create a simple migration that does nothing
            fake_content = f"""from django.db import migrations

class Migration(migrations.Migration):
    \"\"\"
    This is a placeholder migration created to fix a broken dependency.
    It was automatically generated to replace a missing migration.
    \"\"\"

    dependencies = [
        ('admin_panel', '0001_initial'),
    ]

    operations = [
        # No operations - this is just a placeholder
    ]
"""
            try:
                with open(fake_migration_path, 'w', encoding='utf-8') as f:
                    f.write(fake_content)
                created_count += 1
                logger.info(f"Created fake migration {fake_migration_path}")
            except Exception as e:
                logger.error(f"Error creating fake migration {fake_migration_path}: {e}")
    
    logger.info(f"Created {created_count} fake migrations")
    return created_count > 0

if __name__ == "__main__":
    logger.info("Starting migration dependency fix")
    
    # First try to fix the dependencies
    fixed = fix_migration_dependencies()
    
    # If fixing didn't work, create fake migrations as a fallback
    if not fixed:
        logger.info("Creating placeholder migrations as fallback")
        create_fake_migrations()
    
    logger.info("Migration dependency fix completed") 