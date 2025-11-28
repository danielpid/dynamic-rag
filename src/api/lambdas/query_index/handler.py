import json
from llama_index.core import VectorStoreIndex

from common.lambda_utils import initialize_vector_store, build_response

QUESTION_MAX_LENGTH = 256

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
        return build_response(400, {'error': 'No question provided in the request'})

    elif len(question) > QUESTION_MAX_LENGTH:
        return build_response(400, {'message': f'The question cannot exceed the {QUESTION_MAX_LENGTH} characters'})        
    
    try:        
        vector_store = initialize_vector_store()
        
        # We connect to the existing store.
        index = VectorStoreIndex.from_vector_store(vector_store=vector_store)
                
        query_engine = index.as_query_engine()
        response = query_engine.query(question)

        return build_response(200, {'question': question, 'answer': str(response)})

    except Exception as e:
        print(f"Error querying index: {e}")
        return build_response(500, {'error': str(e)})        