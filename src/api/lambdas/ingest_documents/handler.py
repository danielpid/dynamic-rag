import os
from llama_index.readers.s3 import S3Reader
from llama_index.core import StorageContext, VectorStoreIndex

from common.const import response_headers
from common.lambda_utils import initialize_vector_store

FILE_KEY = "stories.txt"

def handler(event, context):
    print("Ingestion Lambda started...")
    
    try:       
        vector_store = initialize_vector_store(add_hnsw_kwargs=True)        
        storage_context = StorageContext.from_defaults(vector_store=vector_store)
        
        documents = S3Reader(bucket=os.environ["DATA_BUCKET_NAME"], key=FILE_KEY).load_data()
        print(f"Loaded {len(documents)} document(s).")

        # This command generates embeddings and INSERTs them into Postgres
        VectorStoreIndex.from_documents(
            documents, 
            storage_context=storage_context, 
            show_progress=True
        )
        
        return {
            'statusCode': 200, 
            'body': f"Ingested {FILE_KEY}"
        }

    except Exception as e:
        print(f"Error ingesting document: {e}")
        return {
            'statusCode': 500, 
            'body': str(e)
        }