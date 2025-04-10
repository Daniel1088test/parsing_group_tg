#!/usr/bin/env python3
"""
Script to check if the Telegram bot token is valid
"""
import os
import sys
import logging
import asyncio
import requests

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger('token_checker')

def check_token_via_api(token):
    """Check if token is valid using Telegram API"""
    url = f"https://api.telegram.org/bot{token}/getMe"
    try:
        response = requests.get(url, timeout=10)
        data = response.json()
        
        if response.status_code == 200 and data.get('ok'):
            bot_info = data.get('result', {})
            logger.info(f"✅ Token is valid! Bot: @{bot_info.get('username')} ({bot_info.get('id')})")
            return True, bot_info
        else:
            error = data.get('description', 'Unknown error')
            logger.error(f"❌ Token is invalid: {error}")
            return False, {'error': error}
    except Exception as e:
        logger.error(f"❌ Error checking token: {e}")
        return False, {'error': str(e)}

def check_environment_token():
    """Check BOT_TOKEN from environment variables"""
    token = os.environ.get('BOT_TOKEN', '')
    if not token:
        logger.error("❌ BOT_TOKEN environment variable is not set!")
        return False, None
    
    logger.info(f"Checking token from environment: {token[:8]}...")
    return check_token_via_api(token)

def check_config_token():
    """Check token from config file"""
    try:
        # Try to import from config
        sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
        from tg_bot.config import TOKEN_BOT
        
        if not TOKEN_BOT:
            logger.error("❌ TOKEN_BOT in config is empty!")
            return False, None
            
        logger.info(f"Checking token from config: {TOKEN_BOT[:8]}...")
        return check_token_via_api(TOKEN_BOT)
    except ImportError:
        logger.error("❌ Cannot import TOKEN_BOT from config")
        return False, None
    except Exception as e:
        logger.error(f"❌ Error checking config token: {e}")
        return False, None

def check_fixed_token():
    """Check hardcoded token"""
    fixed_token = "8102516142:AAFTsVXXujHHKoX2KZGqZXBHPBznfgh7kg0"
    logger.info(f"Checking fixed token: {fixed_token[:8]}...")
    return check_token_via_api(fixed_token)

def main():
    """Main function"""
    logger.info("=== Telegram Bot Token Checker ===")
    
    # Check environment token
    env_valid, env_info = check_environment_token()
    
    # If environment token is invalid, check config token
    if not env_valid:
        config_valid, config_info = check_config_token()
        
        # If config token is also invalid, check fixed token
        if not config_valid:
            fixed_valid, fixed_info = check_fixed_token()
            
            if fixed_valid:
                logger.info("✅ Fixed token is valid! Setting it as BOT_TOKEN environment variable")
                os.environ['BOT_TOKEN'] = "8102516142:AAFTsVXXujHHKoX2KZGqZXBHPBznfgh7kg0"
                return True
            else:
                logger.error("❌ All tokens are invalid!")
                return False
        else:
            logger.info("✅ Config token is valid! Setting it as BOT_TOKEN environment variable")
            os.environ['BOT_TOKEN'] = config_info.get('token', '')
            return True
    else:
        logger.info("✅ Environment token is valid!")
        return True

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1) 