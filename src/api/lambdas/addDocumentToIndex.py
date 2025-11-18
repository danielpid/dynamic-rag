import json
import psycopg2
import os

from aws_lambda_powertools.utilities import parameters

def handle(event, context):
    try:       
        credentials = parameters.get_secret("dynamic-rag/db_creds", transform="json")       
        conn = psycopg2.connect(
            host=os.environ["DB_HOST"],
            port=os.environ["DB_PORT"],
            database=os.environ["DB_NAME"],
            user=credentials["username"],
            password=credentials["password"]
        )

        with conn.cursor() as cur:
            cur.execute("SELECT 1")
            print(cur.fetchone())        

        return {
            'statusCode': 200,
            'body': 'Document added to index successfully!'
        }
    
    except Exception as e:
        print("Error adding document to index:", e)
        return {
            'statusCode': 500,
            'body': json.dumps({'error': str(e)})
        }
    
    finally:
        try:
            if 'conn' in locals() and conn:
                conn.close()
        except Exception:
            pass