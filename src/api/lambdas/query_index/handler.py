import json
from llama_index.core import VectorStoreIndex

from common.const import response_headers
from common.lambda_utils import initialize_vector_store

def handler(event, context):
    print("Query Lambda invoked", event)
    
    question = None

    if 'question' in event:
        question = event['question']
    elif 'body' in event:
        try:
            body_data = json.loads(event['body']) if isinstance(event['body'], str) else event['body']
            question = body_data.get('question', question)
        except Exception:
            pass
            
    if not question:
        return {
            'statusCode': 400,
            'headers': response_headers,
            'body': json.dumps({'error': 'No question provided in the request'})
        }

    try:        
        vector_store = initialize_vector_store()
        
        # We connect to the existing store.
        index = VectorStoreIndex.from_vector_store(vector_store=vector_store)
                
        query_engine = index.as_query_engine()
        response = query_engine.query(question)

        return {            
            'statusCode': 200,
            'headers': response_headers,
            'body': json.dumps({'question': question, 'answer': str(response)})
        }

    except Exception as e:
        print(f"Error querying index: {e}")
        return {
            'statusCode': 500, 
            'headers': response_headers,
            'body': json.dumps({'error': str(e)})
        }