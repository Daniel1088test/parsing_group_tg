#!/usr/bin/env python3
"""
Script to fix Docker deployment issues with TELEGRAM_API_TOKEN
"""
import os
import sys
import logging
import re

# Configure logging
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

def fix_settings_file():
    """Add TELEGRAM_API_TOKEN to settings if missing"""
    settings_paths = [
        'core/settings.py',
        'settings.py'
    ]
    
    for settings_path in settings_paths:
        if not os.path.exists(settings_path):
            continue
            
        logger.info(f"Found settings file: {settings_path}")
        
        # Read the file
        with open(settings_path, 'r', encoding='utf-8') as f:
            content = f.read()
            
        # Check if TELEGRAM_API_TOKEN is already defined
        if 'TELEGRAM_API_TOKEN' in content:
            logger.info("TELEGRAM_API_TOKEN already defined in settings")
            return True
            
        # Add TELEGRAM_API_TOKEN
        token_definition = "\n# Telegram Bot settings\nTELEGRAM_API_TOKEN = os.environ.get('BOT_TOKEN', '8102516142:AAFTsVXXujHHKoX2KZGqZXBHPBznfgh7kg0')\n"
        
        # Find a proper insertion point
        if '# Application definition' in content:
            # Insert before Application definition
            new_content = content.replace('# Application definition', token_definition + '# Application definition')
        else:
            # Append to the end
            new_content = content + token_definition
            
        # Write updated content
        with open(settings_path, 'w', encoding='utf-8') as f:
            f.write(new_content)
            
        logger.info(f"[OK] Added TELEGRAM_API_TOKEN to {settings_path}")
        return True
        
    logger.error("Could not find Django settings file")
    return False

def fix_models_file():
    """Fix BotSettings model to not depend on settings.TELEGRAM_API_TOKEN"""
    models_path = 'admin_panel/models.py'
    
    if not os.path.exists(models_path):
        logger.error(f"Models file not found: {models_path}")
        return False
        
    logger.info(f"Found models file: {models_path}")
    
    # Read the file
    with open(models_path, 'r', encoding='utf-8') as f:
        content = f.read()
        
    # Update models to not depend on settings.TELEGRAM_API_TOKEN
    if 'default=settings.TELEGRAM_API_TOKEN' in content:
        updated_content = re.sub(
            r'bot_token\s*=\s*models\.CharField\(max_length=255,\s*default=settings\.TELEGRAM_API_TOKEN\)',
            r'bot_token = models.CharField(max_length=255, default="8102516142:AAFTsVXXujHHKoX2KZGqZXBHPBznfgh7kg0")',
            content
        )
        
        # Write updated content
        with open(models_path, 'w', encoding='utf-8') as f:
            f.write(updated_content)
            
        logger.info(f"[OK] Fixed models.py to not depend on settings.TELEGRAM_API_TOKEN")
        return True
        
    logger.info("Models file does not need updating")
    return True

def ensure_environment_variables():
    """Ensure all necessary environment variables are set"""
    env_vars = {
        'BOT_TOKEN': '8102516142:AAFTsVXXujHHKoX2KZGqZXBHPBznfgh7kg0',
        'BOT_USERNAME': 'chan_parsing_mon_bot',
        'API_ID': '19840544',
        'API_HASH': 'c839f28bad345082329ec086fca021fa',
        'DJANGO_SETTINGS_MODULE': 'core.settings',
    }
    
    for key, default_value in env_vars.items():
        if key not in os.environ:
            os.environ[key] = default_value
            logger.info(f"Set environment variable {key}={default_value}")
    
    # Write to .env file for persistence
    try:
        env_path = '.env'
        if os.path.exists(env_path):
            # Read existing content
            with open(env_path, 'r', encoding='utf-8') as f:
                lines = f.readlines()
                
            # Extract existing keys
            existing_keys = {}
            for line in lines:
                line = line.strip()
                if line and not line.startswith('#') and '=' in line:
                    key, value = line.split('=', 1)
                    existing_keys[key.strip()] = value.strip()
                    
            # Update with our defaults if missing
            for key, default_value in env_vars.items():
                if key not in existing_keys:
                    existing_keys[key] = default_value
                    
            # Write back to file
            with open(env_path, 'w', encoding='utf-8') as f:
                for key, value in existing_keys.items():
                    f.write(f"{key}={value}\n")
                    
            logger.info(f"Updated .env file with missing environment variables")
        else:
            # Create new .env file
            with open(env_path, 'w', encoding='utf-8') as f:
                for key, value in env_vars.items():
                    f.write(f"{key}={value}\n")
                    
            logger.info(f"Created new .env file with environment variables")
    except Exception as e:
        logger.error(f"Error updating .env file: {e}")
        
    return True

def create_directories():
    """Create required directories if missing"""
    directories = [
        'staticfiles',
        'media',
        'logs/bot',
        'data/sessions',
    ]
    
    for directory in directories:
        if not os.path.exists(directory):
            os.makedirs(directory, exist_ok=True)
            logger.info(f"Created directory: {directory}")
    
    return True

def main():
    """Main function to fix Docker deployment issues"""
    logger.info("=== Starting Docker deployment fix ===")
    
    # Ensure environment variables are set
    ensure_environment_variables()
    
    # Create required directories
    create_directories()
    
    # Fix settings file
    fix_settings_file()
    
    # Fix models file
    fix_models_file()
    
    logger.info("=== Docker deployment fix completed ===")
    logger.info("You can now restart your application")

if __name__ == "__main__":
    main()
    sys.exit(0) 