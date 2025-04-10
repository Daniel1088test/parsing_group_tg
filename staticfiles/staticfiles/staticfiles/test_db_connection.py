import os
import sys
import psycopg2
from dotenv import load_dotenv

def test_connection():
    # Load environment variables
    load_dotenv()
    
    # Get database URL from environment
    database_url = os.getenv('DATABASE_URL')
    
    if not database_url:
        print("ERROR: DATABASE_URL environment variable not found.")
        return False
    
    # Parse database URL manually
    # Format: postgresql://username:password@host:port/dbname
    parts = database_url.split('://', 1)[1]
    auth, rest = parts.split('@', 1)
    username, password = auth.split(':', 1)
    host_port, dbname = rest.split('/', 1)
    
    if ':' in host_port:
        host, port = host_port.split(':', 1)
    else:
        host = host_port
        port = 5432  # default PostgreSQL port
    
    print(f"Connecting to PostgreSQL database...")
    print(f"Host: {host}")
    print(f"Port: {port}")
    print(f"Database: {dbname}")
    print(f"Username: {username}")
    print(f"Password: {'*' * len(password)}")
    
    try:
        # Connect to the database
        conn = psycopg2.connect(
            host=host,
            port=port,
            dbname=dbname,
            user=username,
            password=password
        )
        
        # Create a cursor
        cursor = conn.cursor()
        
        # Execute a simple query
        cursor.execute("SELECT version();")
        
        # Fetch the result
        version = cursor.fetchone()
        print(f"\nSuccessfully connected to PostgreSQL!")
        print(f"PostgreSQL version: {version[0]}")
        
        # Close the cursor and connection
        cursor.close()
        conn.close()
        return True
        
    except Exception as e:
        print(f"\nERROR: Failed to connect to PostgreSQL database.")
        print(f"Error details: {str(e)}")
        return False

if __name__ == "__main__":
    success = test_connection()
    if not success:
        sys.exit(1) 