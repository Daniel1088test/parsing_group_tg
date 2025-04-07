import os
import sys
import dj_database_url

# Print environment variables (masked for security)
print("Environment variables:")
for key in sorted(os.environ.keys()):
    if 'PASSWORD' in key or 'SECRET' in key or key == 'DATABASE_URL':
        print(f"{key}: {'*' * 10}")
    else:
        print(f"{key}: {os.environ.get(key)}")

# Get DATABASE_URL
database_url = os.environ.get('DATABASE_URL')
if not database_url:
    print("\nERROR: DATABASE_URL environment variable not found.")
    sys.exit(1)

print(f"\nFound DATABASE_URL: {'*' * 10}")

# Parse the URL and test connection
try:
    config = dj_database_url.parse(database_url)
    
    print("\nDatabase configuration:")
    for key, value in config.items():
        if key == 'PASSWORD':
            print(f"{key}: {'*' * 10}")
        else:
            print(f"{key}: {value}")
    
    # Import database connector
    if config['ENGINE'] == 'django.db.backends.postgresql':
        import psycopg
        
        print("\nTesting PostgreSQL connection...")
        # Connection parameters to improve stability
        conn_params = {
            'host': config['HOST'],
            'port': config['PORT'],
            'dbname': config['NAME'],
            'user': config['USER'],
            'password': config['PASSWORD'],
            'connect_timeout': 10,
            'keepalives': 1,
            'keepalives_idle': 30,
            'keepalives_interval': 10,
            'keepalives_count': 5,
            'sslmode': 'require'
        }
        
        conn = psycopg.connect(**conn_params)
        
        with conn.cursor() as cur:
            cur.execute("SELECT version();")
            version = cur.fetchone()[0]
            print(f"Connected successfully! PostgreSQL version: {version}")
            
            # Check if we can execute queries
            cur.execute("SELECT 1;")
            result = cur.fetchone()[0]
            print(f"Query test result: {result}")
        
        conn.close()
        print("Connection closed.")
    else:
        print(f"Database engine {config['ENGINE']} not supported by this test script.")
        
except Exception as e:
    print(f"Error: {e}")
    sys.exit(1)

print("\nDatabase test completed successfully!") 