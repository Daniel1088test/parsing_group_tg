#!/usr/bin/env python3
"""
Fix unclosed aiohttp sessions in the codebase
This script modifies bot files to ensure ClientSessions are properly closed
"""
import os
import sys
import logging
import re

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def fix_file(filepath):
    """Fix a single file with unclosed ClientSession"""
    try:
        with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
            content = f.read()
        
        # Check if the file uses ClientSession
        if 'aiohttp.ClientSession' in content or 'ClientSession(' in content:
            logger.info(f"Found ClientSession usage in {filepath}")
            
            # Check if there's already proper session closing
            if 'session.close()' in content or 'await session.close()' in content:
                logger.info(f"Session already properly closed in {filepath}")
                return False
            
            # Define the fix pattern based on file structure
            modified = content
            
            # Case 1: asyncio.run pattern
            if 'asyncio.run(' in content:
                logger.info(f"Fixing asyncio.run pattern in {filepath}")
                # Wrap with try-finally for session cleanup
                if not 'try:' in content[:content.find('asyncio.run(')]:
                    modified = re.sub(
                        r'(asyncio\.run\()',
                        r'try:\n    \1',
                        content
                    )
                
                # Add finally block for cleanup if not already there
                if 'finally:' not in modified:
                    # Add cleanup code at the end
                    cleanup_code = """
# Add proper session cleanup
except Exception as e:
    logger.error(f'Error running bot: {e}')
finally:
    # Close any remaining sessions
    import asyncio
    import aiohttp
    import gc
    import sys
    
    # Find and cancel any session-related tasks
    for task in asyncio.all_tasks() if hasattr(asyncio, 'all_tasks') else asyncio.Task.all_tasks():
        if not task.done() and 'ClientSession' in str(task):
            logger.info(f"Cancelling session task: {task.get_name()}")
            task.cancel()
    
    # Find and close any open ClientSession objects
    if 'aiohttp.client' in sys.modules:
        # Get all ClientSession objects
        sessions = [obj for obj in gc.get_objects() 
                   if str(type(obj)).find('ClientSession') != -1]
        
        for session in sessions:
            if hasattr(session, 'closed') and not session.closed:
                logger.info("Closing unclosed ClientSession")
                try:
                    if hasattr(asyncio, 'run'):
                        asyncio.run(session.close())
                    else:
                        # Fallback for older Python versions
                        loop = asyncio.get_event_loop()
                        if loop.is_running():
                            loop.create_task(session.close())
                        else:
                            loop.run_until_complete(session.close())
                except Exception as e:
                    logger.error(f"Error closing session: {e}")
    
    logger.info('Session cleanup completed')
"""
                    modified += cleanup_code
            
            # Case 2: Async function with client session creation
            elif 'async def' in content and 'ClientSession(' in content:
                logger.info(f"Fixing async function with ClientSession in {filepath}")
                
                # Find session creation patterns
                session_patterns = [
                    r'(\s*)(session\s*=\s*aiohttp\.ClientSession\([^)]*\))',
                    r'(\s*)(session\s*=\s*ClientSession\([^)]*\))',
                    r'(\s*)(async with\s+aiohttp\.ClientSession\([^)]*\)\s+as\s+session:)'
                ]
                
                for pattern in session_patterns:
                    matches = re.findall(pattern, content)
                    if matches:
                        for indentation, match_text in matches:
                            # For regular session creation, add context manager
                            if 'async with' not in match_text:
                                replacement = f"{indentation}async with {match_text.replace('session = ', '')} as session:"
                                modified = modified.replace(match_text, replacement)
                                logger.info(f"Converted to context manager: {match_text}")
            
            # Write modified content back if changes were made
            if modified != content:
                with open(filepath, 'w', encoding='utf-8') as f:
                    f.write(modified)
                logger.info(f"Successfully fixed {filepath}")
                return True
            else:
                logger.info(f"No changes needed for {filepath}")
                return False
        
        return False
    except Exception as e:
        logger.error(f"Error fixing {filepath}: {e}")
        return False

def fix_all_session_files():
    """Find and fix all files with unclosed ClientSession"""
    fixed_files = []
    scanned_files = 0
    
    try:
        logger.info("Starting scan for files with unclosed aiohttp sessions")
        for root, dirs, files in os.walk('.'):
            # Skip virtualenv, node_modules, and similar directories
            if any(skip_dir in root for skip_dir in ['/venv/', '/env/', '/node_modules/', '/.git/']):
                continue
            
            for file in files:
                if file.endswith('.py'):
                    filepath = os.path.join(root, file)
                    scanned_files += 1
                    
                    if fix_file(filepath):
                        fixed_files.append(filepath)
        
        logger.info(f"Scan complete: fixed {len(fixed_files)} of {scanned_files} Python files")
        for file in fixed_files:
            logger.info(f"  - Fixed {file}")
            
        return len(fixed_files) > 0
    except Exception as e:
        logger.error(f"Error scanning files: {e}")
        return False

if __name__ == "__main__":
    success = fix_all_session_files()
    sys.exit(0 if success else 1) 