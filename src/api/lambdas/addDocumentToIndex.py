import json
import os

from aws_lambda_powertools.utilities import parameters
from llama_index.readers.s3 import S3Reader
from llama_index.core import StorageContext, Settings #, SimpleDirectoryReader
from llama_index.llms.openai import OpenAI
from llama_index.embeddings.openai import OpenAIEmbedding
from llama_index.core import VectorStoreIndex
from llama_index.vector_stores.postgres import PGVectorStore

def handler(event, context):
    print("addDocumentToIndex lambda invoked")  
    try:       
        os.environ["TIKTOKEN_CACHE_DIR"] = "/tmp"
        dbCredentials = parameters.get_secret("dynamic-rag/db_creds", transform="json")
        db_name = os.environ["DB_NAME"]
        db_host = os.environ["DB_HOST"]
        db_port = os.environ["DB_PORT"]
        db_username = dbCredentials["username"]
        db_password = dbCredentials["password"]
        keysCredentials = parameters.get_secret("dynamic-rag/openai_api_key", transform="json")
        os.environ["OPENAI_API_KEY"] = keysCredentials["OPENAI_API_KEY"]

        Settings.embed_model = OpenAIEmbedding(api_key=os.environ["OPENAI_API_KEY"])
        Settings.llm = OpenAI(model="gpt-3.5-turbo", temperature=0, api_key=os.environ["OPENAI_API_KEY"])

        # RAG
        print("Loading documents from S3...")
        # documents = SimpleDirectoryReader("../data/stories").load_data()
        documents = S3Reader(bucket="dynamic-rag-data-bucket", key="stories.txt").load_data()
        print(f"Loaded {len(documents)} documents from S3.")
        vector_store = PGVectorStore.from_params(
            database=db_name,
            host=db_host,
            password=db_password,
            port=db_port,
            user=db_username,
            table_name="stories",
            embed_dim=1536,  # openai embedding dimension
            hnsw_kwargs={
                "hnsw_m": 16,
                "hnsw_ef_construction": 64,
                "hnsw_ef_search": 40,
                "hnsw_dist_method": "vector_cosine_ops",
            },
        )
        print("PGVectorStore initialized.")

        storage_context = StorageContext.from_defaults(vector_store=vector_store)
        print("Storage context created.")
        index = VectorStoreIndex.from_documents(
            documents, storage_context=storage_context, show_progress=True
        )
        print("Index created and documents added to vector store.")
        query_engine = index.as_query_engine()
        print("Query engine created.")
        question = "Where are Lira's reports stored?"
        response = query_engine.query(question)        
        print("Response from RAG query:", response)

        return {
            'statusCode': 200,
            # 'body': 'Document added to index successfully'
            'body': json.dumps({'question': question, 'answer': str(response)})
        }
    
    except Exception as e:
        print("Error adding document to index:", e)
        return {
            'statusCode': 500,
            'body': json.dumps({'error': str(e)})
        }    