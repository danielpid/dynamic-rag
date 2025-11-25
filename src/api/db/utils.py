def get_connection():
    import psycopg2
    from aws_lambda_powertools.utilities import parameters
    import os

    dbCredentials = parameters.get_secret("dynamic-rag/db_creds", transform="json")
    db_name = os.environ["DB_NAME"]
    db_host = os.environ["DB_HOST"]
    db_port = os.environ["DB_PORT"]
    db_username = dbCredentials["username"]
    db_password = dbCredentials["password"]
    conn = psycopg2.connect(
        host=db_host,
        port=db_port,
        database=db_name,
        user=db_username,
        password=db_password
    )
    conn.autocommit = True
    return conn

def create_vector_extension():
    from pgvector.psycopg2 import register_vector

    try:
        conn = get_connection()
        with conn.cursor() as cur:
            cur.execute("CREATE EXTENSION IF NOT EXISTS vector;")
            register_vector(conn)
    finally:
        try:
            if 'conn' in locals() and conn:
                conn.close()
        except Exception:
            pass

def check_vector_extension(conn):   
    try: 
        conn = get_connection()
        with conn.cursor() as cur:       
            cur.execute("SELECT typname FROM pg_type WHERE typname = 'vector';")
            print(cur.fetchone())
    finally:
        try:
            if 'conn' in locals() and conn:
                conn.close()
        except Exception:
            pass