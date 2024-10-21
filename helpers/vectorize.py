from django.http import JsonResponse, HttpResponse
from django.views.decorators.csrf import csrf_exempt
import os, psycopg2, pymupdf, json, io, pdfplumber
from openai import OpenAI
import numpy as np
from langchain_text_splitters import RecursiveCharacterTextSplitter
from analytics.models import userData
from django.db import connection
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))


def whatsapp_prompts(required_fields, type):

    PROMPT_FOR_IMAGE = f"""
    identiy the fields: {required_fields} from the following image.
    return the answer in json format. if any of the field is missing, return null in its place

    if you dont know the answer, return an empty json object. dont include any apologies or any other statements in your response

    """

    PROMPT_FOR_DOC = f"""
    identiy the fields: {required_fields} from the following text.
    return the answer in json format. if any of the field is missing, return null in its place

    if you dont know the answer, return an empty json object. dont include any apologies or any other statements in your response

    """

    if type == "image":
        return PROMPT_FOR_IMAGE
    elif type == "doc":
        return PROMPT_FOR_DOC

def split_file(pdf_file): 
    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=100,
        chunk_overlap=15,
        length_function=len,
        is_separator_regex=False,
    )
    document = pymupdf.open(stream=pdf_file, filetype="pdf")
    full_text = ""
    for page_num in range(len(document)):
        page = document.load_page(page_num)
        full_text += page.get_text()

    
    print("full text: ", full_text)

    texts = text_splitter.split_text(full_text)

    return texts

def get_embeddings(chunks):
    embeddings = []
    for chunk in chunks:
        response = client.embeddings.create(input=chunk, model="text-embedding-3-small")
        embeddings.append(response.data[0].embedding)
    print("Successfully created embeddings out of chunks")
    return embeddings

def vectorize(pdf_file):
    try:
        
        chunks = split_file(pdf_file)
        embeddings = get_embeddings(chunks)

        
        with connection.cursor() as cursor:
        
            cursor.execute('''
            CREATE TABLE IF NOT EXISTS text_embeddings (
                id SERIAL PRIMARY KEY,
                chunk TEXT,
                embedding vector(1536)
            )
            ''')
        connection.commit()

        # Insert embeddings into the table
        for i, chunk in enumerate(chunks):
            embedding_array = np.array(embeddings[i])
            with  connection.cursor() as cursor:
                cursor.execute(
                    "INSERT INTO text_embeddings (chunk, embedding) VALUES (%s, %s::vector)",
                    (chunk, embedding_array.tolist())
                )
            connection.commit()
        print("Text Vectorized Successfullly")
        return JsonResponse({"status": 200, "message": "Text vectorized successfully"})

    except Exception as e:
        print(f"An error occurred: {e}")
        return JsonResponse({"status": 500, "message": f"An error occurred: {e}"}, status=500)


def process_chunks(chunks):
    try:
        embeddings = get_embeddings(chunks)

        with connection() as cursor:
        
        
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS text_embeddings (
                    id SERIAL PRIMARY KEY,
                    chunk TEXT,
                    embedding vector(1536)
                )
            ''')

        # Insert embeddings into the table
        for i, chunk in enumerate(chunks):
            embedding_array = np.array(embeddings[i])
            with connection.cursor() as cursor:
                cursor.execute(
                    "INSERT INTO text_embeddings (chunk, embedding) VALUES (%s, %s::vector)",
                    (chunk, embedding_array.tolist())
                )
        return True
    except Exception as e:
        print(f"An error occurred: {e}")
        return False


def get_query_embedding(query):
    response = client.embeddings.create(
        input=query,
        model="text-embedding-ada-002"
    )
    embedding = response.data[0].embedding
    print(type(embedding))
    return embedding

def store_chunk_embedding(chunk, embedding):
    try:
        with connection.cursor() as cursor:
            # Insert the chunk and its embedding into the table
            cursor.execute(
                "INSERT INTO text_embeddings (chunk, embedding) VALUES (%s, %s::vector(1536))",
                (chunk, embedding)
            )
    except Exception as e:
        print(f"Error: {e}")
    return []

# Function to perform cosine similarity search using pgvector
def perform_cosine_similarity_search(query_embedding):
    try:
        # Convert query embedding to string format for SQL
        query_embedding_str = '[' + ','.join(map(str, query_embedding)) + ']'
        print("Query embedding string: ", query_embedding_str)
        
        with connection.cursor() as cursor:
            # Perform the cosine similarity search using parameterized queries
            cursor.execute(
                """
                SELECT
                    te.id,
                    te.chunk AS most_similar_chunk,
                    (te.embedding::vector) <=> %s AS similarity_score
                FROM
                    text_embeddings te
                ORDER BY (te.embedding::vector) <=> %s DESC
                LIMIT 10;
                """,
                [query_embedding_str, query_embedding_str]
            )

            results = cursor.fetchall()
            return results
    except Exception as e:
        print(f"Error: {e}")
    
    return []

# Main function to process and search similar queries
def process_and_search_similar_queries(query):
    # Get the embedding for the query
    query_embedding = get_query_embedding(query)
    
    # Convert query embedding to numpy array of type float64
    query_embedding_array = np.array(query_embedding, dtype=np.float64)
    
    # Perform cosine similarity search
    similar_queries = perform_cosine_similarity_search(query_embedding_array)
    print("similr queries: ", similar_queries)
    return similar_queries


def make_openai_call(combined_query, query_string, userJSON):
    print(combined_query, query_string, userJSON)
    response = client.chat.completions.create(
        model="gpt-3.5-turbo",
        messages=[
            {"role": "system", "content": "You are a helpful assistant. Reply to the point. Dont include any apologies or explanations in your replies."},
            {"role": "user", "content": f"you shall answer the queries asked based on the following text provided: {combined_query}. Try to include all the details and names. Make it as descriptive as possible but take inputs only from the text provided."},
            {"role": "user", "content": f"Personalize your response. greet with name. use these details: {userJSON}"},
            {"role": "user", "content": "{}".format(query_string)}
        ]
    )
    answer = response.choices[0].message.content
    print("answer: ", answer)
    return answer

from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
import json

@csrf_exempt
def query(request):
    try:
        tenant_id = request.headers.get('X-Tenant-Id')
        req_body = json.loads(request.body)

    except json.JSONDecodeError:
        return JsonResponse({"data": {"status": 400, "message": "Invalid JSON body."}}, status=400)

    query_string = req_body.get("query", "")
    phone = req_body.get("phone")

    if not query_string:
        return JsonResponse({"data": {"status": 400, "message": "Query is required."}}, status=400)

    userJSON = userData.objects.filter(tenant_id = tenant_id, phone =phone)
    userJSON_list = list(userJSON.values())  
    userJSON_serialized = json.dumps(userJSON_list)
    print("user json: ", userJSON_serialized)
    print("query string: ", query_string)

    similar_chunks = get_similar_chunks_using_faiss(query_string, userJSON_serialized)
    combined_query = ""

    if similar_chunks:
        combined_query = " ".join([doc.page_content for doc in similar_chunks])

        try:
            openai_response = make_openai_call(combined_query, query_string, userJSON_serialized)
            return HttpResponse(openai_response, status = 200)
        except Exception as e:
            return JsonResponse({"status": 500, "message": f"Error processing query: {str(e)}"})

    else:
        return JsonResponse({"status": 404, "answer": "No relevant answers found."})

def get_docs():

    query = "SELECT chunk from text_embeddings"

    with connection.cursor() as cursor:
        cursor.execute(query)
        result = cursor.fetchall()

    # Extract chunks from the result
    chunks = [row[0] for row in result]
    
    return chunks

from langchain_community.vectorstores import FAISS
from langchain.schema import Document
from langchain_community.embeddings import OpenAIEmbeddings
from analytics.models import FAISSIndex

def get_similar_chunks_using_faiss(query, userJSON):
    try:
        name = "hotels in india.pdf"

        # Fetch the index data from FAISSIndex model
        index_data = FAISSIndex.objects.get(name=name)
        
        # Deserialize FAISS index
        embeddings = OpenAIEmbeddings()
        library = FAISS.deserialize_from_bytes(index_data.index_data, embeddings, allow_dangerous_deserialization=True)

        print("Library: ", library)
        print("FAISS library created.")
        
        # Combine the query and userJSON data
        query = query + json.dumps(userJSON)

        # Perform similarity search
        answer = library.similarity_search(query)
        print(f"Answer retrieved: {answer}")

        return answer

    except FAISSIndex.DoesNotExist:
        print("Error: FAISS index not found.")
        return None

    except ValueError as e:
        print(f"Error in FAISS deserialization: {str(e)}")
        return None

    except Exception as e:
        print(f"An unexpected error occurred: {str(e)}")
        return None


@csrf_exempt
def vectorize_FAISS(pdf_file, file_name, json_data, tenant_id):
    
    name = file_name
    print("name : ", name)
    chunks = split_file(pdf_file)
    
    doc_objects = [Document(page_content=chunk) for chunk in chunks]
    
    embedding = OpenAIEmbeddings()
    print("Embeddings created.")

    try:
        existing_faiss_index = FAISSIndex.objects.get(name=name)
        print("Existing FAISS index found. Updating it.")
        
        existing_library = FAISS.deserialize_from_bytes(existing_faiss_index.index_data, embeddings= embedding, allow_dangerous_deserialization=True)
        
        existing_library.add_documents(doc_objects)
        
        serialized_index = existing_library.serialize_to_bytes()
        
        existing_faiss_index.index_data = serialized_index
        existing_faiss_index.save()
        print("Existing FAISS index updated.")
        
    except FAISSIndex.DoesNotExist:
        print("No existing FAISS index found. Creating a new one.")
        
        library = FAISS.from_documents(doc_objects, embedding)
        
        serialized_index = library.serialize_to_bytes()
        
        faiss_index = FAISSIndex(name=name, index_data=serialized_index, json_data = json_data, tenant_id = tenant_id)
        faiss_index.save()
        print("New FAISS index saved.")

    return JsonResponse({"status": 200, "message": "Text vectorized successfully"})


@csrf_exempt
def handle_media_uploads(request):
    if request.method == 'POST':
        try:

            print("rcvd reeq: " , request)

            tenant_id = request.headers.get('X-Tenant-Id')
            user_data = request.headers.get('user-data')
            print("user data: ", user_data)
            user_data = json.loads(user_data)
            user_data['tenant_id'] = tenant_id
            
            existing_faiss_index = FAISSIndex.objects.get(tenant_id = tenant_id)

            required_fields = list(json.loads(existing_faiss_index.json_data).values())
            print("Req fields: ", required_fields)
            files = request.FILES

            if not files:
                prompt = whatsapp_prompts(required_fields=required_fields, type="image")
                data = json.loads(request.body)
                image_buffer = data.get('image_buffer')

                content = [
                    {
                        'type': "text",
                        'text': prompt
                    },
                    {
                        'type': 'image_url',
                        'image_url': {
                            'url': f"data:image/webp;base64,{image_buffer}"
                        }
                    }
                ]

            else:
                prompt = whatsapp_prompts(required_fields=required_fields, type="doc")
                pdf_file = request.FILES.get('pdf')

                if not pdf_file:
                    return JsonResponse({"error": "No PDF file received."}, status=400)

                pdf_stream = io.BytesIO(pdf_file.read())

                extracted_text = ''
                with pdfplumber.open(pdf_stream) as pdf:
                    for page in pdf.pages:
                        extracted_text += page.extract_text()
                
                content = [
                    {
                        'type': "text",
                        'text': prompt
                    },
                    {
                        'type': 'text',
                        'text': extracted_text
                    }
                ]
            print("CONTENT: ", content)
            payload = {
                'model': "gpt-4o-mini",
                'messages': [
                    {
                        'role': "user",
                        'content': content
                    }
                ]
            }
            response = client.chat.completions.create(
                model="gpt-4o-mini",
                messages= payload['messages']
            )

            if response.choices:
                answer = response.choices[0].message.content
                start_index = answer.find('{')
                end_index = answer.rfind('}') + 1
                answer = answer[start_index:end_index].strip()
                answer = json.loads(answer)
            else:
                return JsonResponse({"error": "No response from the model."}, status=500)
            
            user_data['data'] = answer

            print("json response: ", user_data)


            return JsonResponse({"success": answer})


        except Exception as e:
            print(e)
            return JsonResponse({"error": "Error processing the PDF file."}, status=500)

    return JsonResponse({"error": "Invalid request method. Use POST."}, status=405)