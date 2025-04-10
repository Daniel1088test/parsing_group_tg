import re

def parse_username_from_text(text):
    """
    Extract Telegram channel username from text.
    
    Looks for patterns like:
    - @username
    - https://t.me/username
    - t.me/username
    - telegram.me/username
    - https://telegram.me/username
    - telegram.me/joinchat/invite_code
    - t.me/joinchat/invite_code
    
    Returns:
        str or None: The username/channel identifier if found, None otherwise
    """
    if not text:
        return None
        
    # Try to match @username format
    username_match = re.search(r'@([a-zA-Z0-9_]{5,32})', text)
    if username_match:
        return username_match.group(1)
    
    # Try to match t.me or telegram.me links
    url_match = re.search(r'(?:https?://)?(?:t|telegram)\.me/([a-zA-Z0-9_]{5,32})', text)
    if url_match:
        return url_match.group(1)
    
    # Try to match private invite links
    invite_match = re.search(r'(?:https?://)?(?:t|telegram)\.me/(?:joinchat|join)/([a-zA-Z0-9_-]+)', text)
    if invite_match:
        return 'joinchat/' + invite_match.group(1)
    
    # Try to match private channel links with ID
    private_match = re.search(r'(?:https?://)?(?:t|telegram)\.me/c/(\d+)', text)
    if private_match:
        return 'c/' + private_match.group(1)
    
    return None 