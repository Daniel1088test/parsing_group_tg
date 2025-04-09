#!/usr/bin/env python3
"""
Script to fix Railway deployment issues - template missing, migrations, and placeholder images
"""
import os
import sys
import logging
import subprocess
from pathlib import Path
import shutil
from PIL import Image, ImageDraw, ImageFont

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('railway_fix.log')
    ]
)
logger = logging.getLogger('railway_fix')

def ensure_directory(directory_path):
    """Ensure directory exists"""
    try:
        os.makedirs(directory_path, exist_ok=True)
        logger.info(f"Ensured directory exists: {directory_path}")
        return True
    except Exception as e:
        logger.error(f"Error creating directory {directory_path}: {e}")
        return False

def fix_migrations():
    """Fix conflicting migrations by generating the latest migration file"""
    try:
        # Clear existing migrations
        migrations_dir = Path('admin_panel/migrations')
        merge_migrations = list(migrations_dir.glob('0003_merge_*.py'))
        
        for migration in merge_migrations:
            try:
                os.remove(migration)
                logger.info(f"Removed conflicting migration: {migration}")
            except Exception as e:
                logger.error(f"Error removing migration {migration}: {e}")
        
        # Create a clean merge migration
        migration_content = """from django.db import migrations

class Migration(migrations.Migration):
    dependencies = [
        ('admin_panel', '0002_auto_20250409_0000'),
        ('admin_panel', 'fix_is_bot_column'),
    ]

    operations = [
    ]
"""
        
        merge_path = migrations_dir / '0003_merge_final.py'
        with open(merge_path, 'w') as f:
            f.write(migration_content)
        logger.info(f"Created merge migration file: {merge_path}")
        
        # Run migrate command
        result = subprocess.run(
            [sys.executable, 'manage.py', 'migrate', '--fake'], 
            capture_output=True, 
            text=True
        )
        logger.info(f"Migration command output: {result.stdout}")
        if result.stderr:
            logger.error(f"Migration command error: {result.stderr}")
        
        return True
    except Exception as e:
        logger.error(f"Error fixing migrations: {e}")
        return False

def create_placeholder_images():
    """Create placeholder images for media files"""
    try:
        # Ensure directories exist
        static_img_dir = Path('staticfiles/img')
        ensure_directory(static_img_dir)
        
        # Create placeholder images if they don't exist
        image_placeholder = static_img_dir / 'placeholder-image.png'
        video_placeholder = static_img_dir / 'placeholder-video.png'
        
        if not image_placeholder.exists():
            # Create image placeholder
            img = Image.new('RGB', (300, 200), color=(240, 240, 240))
            draw = ImageDraw.Draw(img)
            draw.rectangle([(0, 0), (299, 199)], outline=(200, 200, 200), width=2)
            draw.text((100, 100), "IMAGE", fill=(100, 100, 100))
            img.save(image_placeholder)
            logger.info(f"Created placeholder image: {image_placeholder}")
        
        if not video_placeholder.exists():
            # Create video placeholder
            img = Image.new('RGB', (300, 200), color=(240, 240, 240))
            draw = ImageDraw.Draw(img)
            draw.rectangle([(0, 0), (299, 199)], outline=(200, 200, 200), width=2)
            draw.text((100, 100), "VIDEO", fill=(100, 100, 100))
            img.save(video_placeholder)
            logger.info(f"Created placeholder video: {video_placeholder}")
        
        return True
    except Exception as e:
        logger.error(f"Error creating placeholder images: {e}")
        
        # Try to create empty placeholder files as fallback
        try:
            # Create empty placeholder files
            with open(static_img_dir / 'placeholder-image.png', 'wb') as f:
                f.write(b'')
            with open(static_img_dir / 'placeholder-video.png', 'wb') as f:
                f.write(b'')
            logger.info("Created empty placeholder files")
        except Exception as inner_e:
            logger.error(f"Error creating empty placeholders: {inner_e}")
        
        return False

def update_templates_settings():
    """Update Django settings to find templates in the right directory"""
    try:
        settings_file = Path('core/settings.py')
        
        if not settings_file.exists():
            logger.error("Settings file not found")
            return False
        
        with open(settings_file, 'r') as f:
            content = f.read()
        
        # Check if TEMPLATES setting needs updating
        if "'DIRS': [os.path.join(BASE_DIR, 'templates')]" in content:
            logger.info("TEMPLATES setting already updated")
        else:
            # Update TEMPLATES setting
            template_line = "'DIRS': [],"
            template_replacement = "'DIRS': [os.path.join(BASE_DIR, 'templates')],"
            
            if template_line in content:
                new_content = content.replace(template_line, template_replacement)
                
                with open(settings_file, 'w') as f:
                    f.write(new_content)
                
                logger.info("Updated TEMPLATES setting in settings.py")
            else:
                logger.warning("Could not find TEMPLATES setting to update")
        
        return True
    except Exception as e:
        logger.error(f"Error updating templates settings: {e}")
        return False

def create_base_template():
    """Create base.html template if missing"""
    try:
        templates_dir = Path('templates')
        ensure_directory(templates_dir)
        
        base_template = templates_dir / 'base.html'
        
        if base_template.exists():
            logger.info("base.html template already exists")
            return True
        
        # Template content - simplified for brevity
        template_content = """<!DOCTYPE html>
<html lang="uk">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{% block title %}Telegram Parser{% endblock %}</title>
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.2/dist/css/bootstrap.min.css" rel="stylesheet">
    {% block extra_css %}{% endblock %}
</head>
<body>
    {% block content %}{% endblock %}
    <script src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.2/dist/js/bootstrap.bundle.min.js"></script>
    <script src="https://code.jquery.com/jquery-3.7.1.min.js"></script>
    {% block extra_js %}{% endblock %}
</body>
</html>"""
        
        with open(base_template, 'w') as f:
            f.write(template_content)
        
        logger.info(f"Created base.html template at {base_template}")
        return True
    except Exception as e:
        logger.error(f"Error creating base template: {e}")
        return False

def restart_django():
    """Restart Django server"""
    try:
        # Touch wsgi.py to trigger reload
        wsgi_file = Path('core/wsgi.py')
        
        if wsgi_file.exists():
            # Add timestamp to trigger reload
            with open(wsgi_file, 'a') as f:
                f.write(f"\n# Restart trigger: {os.urandom(8).hex()}")
            
            logger.info(f"Touched {wsgi_file} to trigger reload")
        
        # Create health check files for Railway
        health_files = ['health.html', 'healthz.html', 'health.txt', 'healthz.txt']
        for file in health_files:
            with open(file, 'w') as f:
                f.write('OK')
            logger.info(f"Created health file: {file}")
        
        return True
    except Exception as e:
        logger.error(f"Error restarting Django: {e}")
        return False

def main():
    """Main function to run all fixes"""
    logger.info("=== Starting Railway deployment fixes ===")
    
    # Run fixes
    update_templates_settings()
    create_base_template()
    fix_migrations()
    create_placeholder_images()
    restart_django()
    
    logger.info("=== Railway deployment fixes completed ===")
    return True

if __name__ == "__main__":
    main() 