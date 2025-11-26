import os

from aws_lambda_powertools.utilities import parameters
from llama_index.core import Settings
from llama_index.llms.openai import OpenAI
from llama_index.embeddings.openai import OpenAIEmbedding
from llama_index.vector_stores.postgres import PGVectorStore

from .const import model

ONE_DAY_IN_SECONDS = 86400

dbCredentials = parameters.get_secret("dynamic-rag/db_creds", transform="json", max_age=ONE_DAY_IN_SECONDS)
keysCredentials = parameters.get_secret("dynamic-rag/openai_api_key", transform="json", max_age=ONE_DAY_IN_SECONDS)

def initialize_vector_store(add_hnsw_kwargs=False):
    os.environ["TIKTOKEN_CACHE_DIR"] = "/tmp"        
    
    openai_api_key = keysCredentials["OPENAI_API_KEY"]
    os.environ["OPENAI_API_KEY"] = openai_api_key
    
    Settings.embed_model = OpenAIEmbedding(api_key=openai_api_key)
    Settings.llm = OpenAI(model=model, api_key=openai_api_key, temperature=0)

    vector_store_params = {
        "database": os.environ["DB_NAME"],
        "host": os.environ["DB_HOST"],
        "password": dbCredentials["password"],
        "port": os.environ["DB_PORT"],
        "user": dbCredentials["username"],
        "table_name": "stories",
        "embed_dim": 1536,
    }

    if add_hnsw_kwargs:
        vector_store_params["hnsw_kwargs"]= {
            "hnsw_m": 16,
            "hnsw_ef_construction": 64,
            "hnsw_ef_search": 40,
            "hnsw_dist_method": "vector_cosine_ops",
        }

    vector_store = PGVectorStore.from_params(**vector_store_params)

    return vector_store