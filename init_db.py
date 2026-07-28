import os
from dotenv import load_dotenv
from sqlalchemy import create_engine, text
import pymysql

load_dotenv()

db_uri = os.environ.get('DB_URI')
if not db_uri or not db_uri.startswith('mysql'):
    print("Error: DB_URI is not set to a MySQL connection string.")
    exit(1)

# Extract connection details without the database name
# E.g. mysql+pymysql://root:password@localhost/college_events
# We want mysql+pymysql://root:password@localhost

base_uri = db_uri.rsplit('/', 1)[0]
db_name = db_uri.rsplit('/', 1)[1]

print(f"Connecting to MySQL server at {base_uri} to create database '{db_name}'...")

try:
    engine = create_engine(base_uri)
    with engine.connect() as conn:
        conn.execute(text(f"CREATE DATABASE IF NOT EXISTS {db_name}"))
    print(f"Database '{db_name}' created or already exists.")
except Exception as e:
    print(f"Failed to create database: {e}")
    exit(1)
