import os
import pymysql
import pymysql.cursors
from urllib.parse import urlparse
from config import Config

def get_db_connection():
    db_uri = Config.SQLALCHEMY_DATABASE_URI
    
    # Parse DB_URI: mysql+pymysql://root:1234@localhost/college_events
    if not db_uri or 'mysql' not in db_uri:
        raise ValueError('Database URI not configured correctly for PyMySQL.')
        
    parsed = urlparse(db_uri)
    
    host = parsed.hostname or 'localhost'
    port = parsed.port or 3306
    user = parsed.username or 'root'
    password = parsed.password or ''
    database = parsed.path.lstrip('/') if parsed.path else 'college_events'
    
    connection = pymysql.connect(
        host=host,
        port=port,
        user=user,
        password=password,
        database=database,
        cursorclass=pymysql.cursors.DictCursor,
        autocommit=False
    )
    return connection
