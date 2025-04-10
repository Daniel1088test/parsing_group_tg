#!/usr/bin/env python3
"""
Script to fix templates and ensure all required directories for web serving exist
"""
import os
import sys
import logging
import django

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('fix_templates_and_aiohttp.log')
    ]
)
logger = logging.getLogger('fix_templates')

# Set up Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
try:
    django.setup()
    from django.conf import settings
    logger.info("Django initialized successfully")
except Exception as e:
    logger.error(f"Error initializing Django: {e}")
    sys.exit(1)

def ensure_directories_exist():
    """Ensure that all required directories exist"""
    try:
        # Create required directories
        required_dirs = [
            os.path.join(settings.BASE_DIR, 'templates'),
            os.path.join(settings.BASE_DIR, 'templates', 'admin_panel'),
            os.path.join(settings.BASE_DIR, 'static'),
            os.path.join(settings.BASE_DIR, 'static', 'img'),
            os.path.join(settings.BASE_DIR, 'static', 'health'),
            os.path.join(settings.BASE_DIR, 'staticfiles'),
            os.path.join(settings.BASE_DIR, 'staticfiles', 'img'),
            os.path.join(settings.BASE_DIR, 'staticfiles', 'health'),
            os.path.join(settings.BASE_DIR, 'media'),
            os.path.join(settings.BASE_DIR, 'media', 'messages'),
            os.path.join(settings.BASE_DIR, 'logs'),
        ]
        
        for directory in required_dirs:
            if not os.path.exists(directory):
                os.makedirs(directory, exist_ok=True)
                logger.info(f"Created directory: {directory}")
        
        logger.info("All required directories exist")
        return True
    except Exception as e:
        logger.error(f"Error creating directories: {e}")
        return False

def create_health_files():
    """Create health check files in static and staticfiles directories"""
    try:
        health_files = [
            {'path': os.path.join(settings.BASE_DIR, 'static', 'health.txt'), 'content': 'OK'},
            {'path': os.path.join(settings.BASE_DIR, 'static', 'healthz.txt'), 'content': 'OK'},
            {'path': os.path.join(settings.BASE_DIR, 'static', 'health.html'), 'content': '<html><body>OK</body></html>'},
            {'path': os.path.join(settings.BASE_DIR, 'static', 'healthz.html'), 'content': '<html><body>OK</body></html>'},
            {'path': os.path.join(settings.BASE_DIR, 'staticfiles', 'health.txt'), 'content': 'OK'},
            {'path': os.path.join(settings.BASE_DIR, 'staticfiles', 'healthz.txt'), 'content': 'OK'},
            {'path': os.path.join(settings.BASE_DIR, 'staticfiles', 'health.html'), 'content': '<html><body>OK</body></html>'},
            {'path': os.path.join(settings.BASE_DIR, 'staticfiles', 'healthz.html'), 'content': '<html><body>OK</body></html>'},
            {'path': os.path.join(settings.BASE_DIR, 'health.txt'), 'content': 'OK'},
            {'path': os.path.join(settings.BASE_DIR, 'healthz.txt'), 'content': 'OK'},
            {'path': os.path.join(settings.BASE_DIR, 'health.html'), 'content': '<html><body>OK</body></html>'},
            {'path': os.path.join(settings.BASE_DIR, 'healthz.html'), 'content': '<html><body>OK</body></html>'},
        ]
        
        for file in health_files:
            with open(file['path'], 'w') as f:
                f.write(file['content'])
            logger.info(f"Created health file: {file['path']}")
        
        logger.info("All health files created")
        return True
    except Exception as e:
        logger.error(f"Error creating health files: {e}")
        return False

def create_placeholder_images():
    """Create placeholder images for media files"""
    try:
        # Try to use PIL if available
        try:
            from PIL import Image, ImageDraw, ImageFont
            
            # Create image placeholder
            img_placeholder_path = os.path.join(settings.BASE_DIR, 'static', 'img', 'placeholder-image.png')
            if not os.path.exists(img_placeholder_path):
                img = Image.new('RGB', (300, 200), color=(240, 240, 240))
                draw = ImageDraw.Draw(img)
                draw.rectangle([(0, 0), (299, 199)], outline=(200, 200, 200), width=2)
                draw.text((150, 100), "IMAGE", fill=(100, 100, 100))
                img.save(img_placeholder_path)
                logger.info(f"Created placeholder image: {img_placeholder_path}")
            
            # Create video placeholder
            video_placeholder_path = os.path.join(settings.BASE_DIR, 'static', 'img', 'placeholder-video.png')
            if not os.path.exists(video_placeholder_path):
                img = Image.new('RGB', (300, 200), color=(240, 240, 240))
                draw = ImageDraw.Draw(img)
                draw.rectangle([(0, 0), (299, 199)], outline=(200, 200, 200), width=2)
                draw.text((150, 100), "VIDEO", fill=(100, 100, 100))
                img.save(video_placeholder_path)
                logger.info(f"Created placeholder video: {video_placeholder_path}")
            
            # Copy placeholders to staticfiles
            import shutil
            staticfiles_img_dir = os.path.join(settings.BASE_DIR, 'staticfiles', 'img')
            os.makedirs(staticfiles_img_dir, exist_ok=True)
            
            shutil.copy2(img_placeholder_path, os.path.join(staticfiles_img_dir, 'placeholder-image.png'))
            shutil.copy2(video_placeholder_path, os.path.join(staticfiles_img_dir, 'placeholder-video.png'))
            logger.info("Copied placeholders to staticfiles directory")
            
        except ImportError:
            logger.warning("PIL not available, creating simple placeholder files")
            
            # Create simple placeholder files
            img_placeholder_path = os.path.join(settings.BASE_DIR, 'static', 'img', 'placeholder-image.png')
            video_placeholder_path = os.path.join(settings.BASE_DIR, 'static', 'img', 'placeholder-video.png')
            
            with open(img_placeholder_path, 'wb') as f:
                f.write(b'')
            with open(video_placeholder_path, 'wb') as f:
                f.write(b'')
            
            # Copy placeholders to staticfiles
            staticfiles_img_dir = os.path.join(settings.BASE_DIR, 'staticfiles', 'img')
            os.makedirs(staticfiles_img_dir, exist_ok=True)
            
            import shutil
            shutil.copy2(img_placeholder_path, os.path.join(staticfiles_img_dir, 'placeholder-image.png'))
            shutil.copy2(video_placeholder_path, os.path.join(staticfiles_img_dir, 'placeholder-video.png'))
            logger.info("Created and copied empty placeholder files")
        
        logger.info("Placeholders created successfully")
        return True
    except Exception as e:
        logger.error(f"Error creating placeholder images: {e}")
        return False

def run_collectstatic():
    """Run Django's collectstatic command"""
    try:
        from django.core.management import call_command
        call_command('collectstatic', '--noinput')
        logger.info("Collectstatic completed successfully")
        return True
    except Exception as e:
        logger.error(f"Error running collectstatic: {e}")
        return False

def main():
    """Main function"""
    logger.info("Starting fix templates script")
    
    # Ensure directories exist
    ensure_directories_exist()
    
    # Create health files
    create_health_files()
    
    # Create placeholder images
    create_placeholder_images()
    
    # Run collectstatic
    run_collectstatic()
    
    logger.info("Fix templates script completed")
    return True

if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        logger.error(f"Unhandled error: {e}")
        sys.exit(1) 