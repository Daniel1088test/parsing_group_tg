#!/usr/bin/env python
"""
This script encodes a Telethon session file to base64 so it can be stored
in the TELETHON_SESSION environment variable on Railway.

Usage:
python encode_telethon_session.py <session_file>

Example:
python encode_telethon_session.py telethon_session.session
"""

import os
import sys
import base64

def encode_session_file(file_path):
    """Encode a session file to base64 for use in environment variables"""
    if not os.path.exists(file_path):
        print(f"Error: File {file_path} does not exist")
        return None
        
    try:
        with open(file_path, 'rb') as f:
            session_data = f.read()
            encoded_data = base64.b64encode(session_data).decode('utf-8')
            return encoded_data
    except Exception as e:
        print(f"Error encoding file: {e}")
        return None

def main():
    # Check arguments
    if len(sys.argv) != 2:
        print("Usage: python encode_telethon_session.py <session_file>")
        print("Example: python encode_telethon_session.py telethon_session.session")
        sys.exit(1)
        
    file_path = sys.argv[1]
    
    # Encode the file
    encoded_data = encode_session_file(file_path)
    
    if encoded_data:
        print("\nSession file successfully encoded!")
        print(f"File size: {os.path.getsize(file_path)} bytes")
        print(f"Encoded length: {len(encoded_data)} characters")
        print("\nAdd this to your Railway environment variables:")
        print("Variable name: TELETHON_SESSION")
        print(f"Value: {encoded_data}")
        print("\nIMPORTANT: Make sure to add this as a secret environment variable in Railway dashboard.")
        
if __name__ == "__main__":
    main() 