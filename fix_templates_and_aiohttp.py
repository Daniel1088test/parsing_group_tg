#!/usr/bin/env python3
"""
Script to fix various issues with templates and settings
"""
import os
import sys
import re
import logging
import django
from pathlib import Path

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Replace the standard StreamHandler with one that has proper encoding
for handler in logger.handlers:
    if isinstance(handler, logging.StreamHandler):
        logger.removeHandler(handler)

# Add new handler with proper encoding
console_handler = logging.StreamHandler(sys.stdout)
console_handler.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))
logger.addHandler(console_handler)

def fix_settings():
    """Add TELEGRAM_API_TOKEN to Django settings"""
    try:
        # Try to locate settings.py
        settings_files = [
            'core/settings.py',
            'settings.py',
        ]
        
        settings_path = None
        for path in settings_files:
            if os.path.exists(path):
                settings_path = path
                break
        
        if not settings_path:
            logger.error("Could not find Django settings file")
            return False
            
        logger.info(f"Found settings file at {settings_path}")
        
        # Read the settings file
        with open(settings_path, 'r', encoding='utf-8') as f:
            content = f.read()
            
        # Check if TELEGRAM_API_TOKEN already exists
        if 'TELEGRAM_API_TOKEN' in content:
            logger.info("TELEGRAM_API_TOKEN already exists in settings")
            return True
            
        # Add TELEGRAM_API_TOKEN to settings, getting it from environment
        new_setting = "\n# Telegram API Token from environment\nTELEGRAM_API_TOKEN = os.environ.get('BOT_TOKEN', '8102516142:AAFTsVXXujHHKoX2KZGqZXBHPBznfgh7kg0')\n"
        
        # Find a good place to insert the setting
        if '# Application definition' in content:
            content = content.replace('# Application definition', new_setting + '# Application definition')
        else:
            # Add it near the end of the file
            content += new_setting
            
        # Write updated content
        with open(settings_path, 'w', encoding='utf-8') as f:
            f.write(content)
            
        logger.info("[OK] Added TELEGRAM_API_TOKEN to settings")
        return True
        
    except Exception as e:
        logger.error(f"Error fixing settings: {e}")
        return False

def fix_models():
    """Fix the BotSettings model to handle missing TELEGRAM_API_TOKEN"""
    try:
        models_path = 'admin_panel/models.py'
        if not os.path.exists(models_path):
            logger.error(f"Models file not found at {models_path}")
            return False
            
        with open(models_path, 'r', encoding='utf-8') as f:
            content = f.read()
            
        # Update the BotSettings model to handle missing TELEGRAM_API_TOKEN
        updated_content = re.sub(
            r'bot_token\s*=\s*models\.CharField\(max_length=255,\s*default=settings\.TELEGRAM_API_TOKEN\)',
            'bot_token = models.CharField(max_length=255, default="8102516142:AAFTsVXXujHHKoX2KZGqZXBHPBznfgh7kg0")',
            content
        )
        
        if content != updated_content:
            with open(models_path, 'w', encoding='utf-8') as f:
                f.write(updated_content)
                
            logger.info("[OK] Fixed BotSettings model")
            return True
        else:
            logger.info("No changes needed for BotSettings model")
            return True
            
    except Exception as e:
        logger.error(f"Error fixing models: {e}")
        return False

def update_env_file():
    """Make sure environment variables are properly set in .env file"""
    try:
        env_path = '.env'
        if not os.path.exists(env_path):
            logger.warning(".env file not found, creating a new one")
            with open(env_path, 'w', encoding='utf-8') as f:
                f.write("# Django settings\n")
                f.write("BOT_TOKEN=8102516142:AAFTsVXXujHHKoX2KZGqZXBHPBznfgh7kg0\n")
                f.write("BOT_USERNAME=chan_parsing_mon_bot\n")
            logger.info("[OK] Created basic .env file")
            return True
            
        # Read existing .env
        with open(env_path, 'r', encoding='utf-8') as f:
            content = f.read()
            
        # Make sure BOT_TOKEN and BOT_USERNAME are defined
        if not re.search(r'BOT_TOKEN\s*=', content):
            content += "\nBOT_TOKEN=8102516142:AAFTsVXXujHHKoX2KZGqZXBHPBznfgh7kg0\n"
            logger.info("Added BOT_TOKEN to .env")
            
        if not re.search(r'BOT_USERNAME\s*=', content):
            content += "\nBOT_USERNAME=chan_parsing_mon_bot\n"
            logger.info("Added BOT_USERNAME to .env")
            
        # Write updated content if changed
        with open(env_path, 'w', encoding='utf-8') as f:
            f.write(content)
            
        logger.info("[OK] Updated .env file")
        return True
        
    except Exception as e:
        logger.error(f"Error updating .env file: {e}")
        return False

def setup_django_environment():
    """Setup Django environment to test settings"""
    try:
        os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
        os.environ['BOT_TOKEN'] = "8102516142:AAFTsVXXujHHKoX2KZGqZXBHPBznfgh7kg0"
        os.environ['BOT_USERNAME'] = "chan_parsing_mon_bot"
        
        django.setup()
        
        # Check if TELEGRAM_API_TOKEN is available
        from django.conf import settings
        if hasattr(settings, 'TELEGRAM_API_TOKEN'):
            logger.info(f"[OK] TELEGRAM_API_TOKEN is now available in settings: {settings.TELEGRAM_API_TOKEN}")
            return True
        else:
            logger.warning("TELEGRAM_API_TOKEN still not available in settings")
            return False
            
    except Exception as e:
        logger.error(f"Error setting up Django environment: {e}")
        return False

def main():
    """Main function to fix all issues"""
    logger.info("=== Starting fix for templates and settings ===")
    
    # Update environment variables
    update_env_file()
    
    # Fix Django settings
    fix_settings()
    
    # Fix models
    fix_models()
    
    # Test Django setup
    setup_django_environment()
    
    logger.info("=== Fixes completed ===")
    return True

if __name__ == "__main__":
    main()
    sys.exit(0) 