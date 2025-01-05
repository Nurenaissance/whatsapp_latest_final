import os
import json
from django.views.decorators.csrf import csrf_exempt
from django.http import JsonResponse
from .tables import get_db_connection, table_mappings
from openai import OpenAI
import pandas as pd
import numpy as np
from tenant.models import Tenant
from contacts.models import Contact
from simplecrm.middleware import TenantMiddleware
from django.db import transaction, connection

import logging
from .tasks import bulk_upload_contacts

# Assuming df is your DataFrame
default_timestamp = '1970-01-01 00:00:00'

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
client = OpenAI(api_key=OPENAI_API_KEY)

def get_tableFields(table_name):
    query = f"SELECT * FROM {table_name} LIMIT 0"  # Use LIMIT 0 to avoid fetching actual data
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute(query)
        column_names = [desc[0] for desc in cursor.description]
    except Exception as e:
        print(f"Error fetching table fields: {e}")
        raise
    finally:
        cursor.close()
        conn.close()
    
    return column_names

SYSTEM_PROMPT = """
You are a helpful assistant who answers STRICTLY to what is asked, based on the info provided. 
DO NOT ADD DATA FROM THE INTERNET. 
Keep your answers concise and only the required information

Map the given two lists with each other.
Fields most similar to each other should be mapped together.
Return only the mapped dictionary in JSON format without nesting.
Skip createdBy_id, tenant_id, template_key, isActive, and createdOn.
The 'phone' and 'name' fields should be mandatorily mapped to their most similar fields.
You can map name to first_name or last_name, but not to both.

If you are not sure about mapping a field, keep it under 'customField' list.

Input Sample: list1: ['name', 'phone', 'email', 'address', 'city'], list2: ['name', 'phone', 'email', 'address', 'description', 'createdBy', 'createdOn', 'isActive', 'tenant', 'template_key', 'last_seen', 'last_delivered', 'last_replied', 'customField']
Output Sample: {'name': 'name', 'phone': 'phone', 'email': 'email', 'customField': ['address', 'city']}
"""



def mappingFunc(list1, list2):
    # Filter out 'id' fields from both lists (case insensitive)
    list1_filtered = [item for item in list1 if item.lower() != 'id']
    list2_filtered = [item for item in list2 if item.lower() != 'id']
    
    print("Filtered List1: ", list1_filtered)
    print("Filtered List2: ", list2_filtered)

    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "developer", "content": SYSTEM_PROMPT},
                {"role": "user", "content": f"Map these two lists with each other. List1: {list1_filtered}, List2: {list2_filtered}."}
            ]
        )
        field_mapping =  response.choices[0].message.content
        
        start = field_mapping.find('{')
        end = field_mapping.find('}')
        field_mapping = field_mapping[start:end + 1]
        field_mapping_json = json.loads(field_mapping)
        print(field_mapping_json)

        return field_mapping_json
    except Exception as e:
        print(f"Error during mapping: {e}")
        raise

@csrf_exempt
def upload_file(request, df):
    if request.method == 'POST':
        try:
            print("Entering upload file")
            print("df: ", df[:5])
            
            model_name = request.POST.get('model_name')
            xls_file = request.FILES.get('file')
            tenant_id = request.headers.get('X-Tenant-Id')
            
            print("Received model_name: ", model_name)
            
            if not (xls_file.name.endswith('.xls') or xls_file.name.endswith('.xlsx') or xls_file.name.endswith('.csv')):
                return JsonResponse({"error": "File is not in XLS/XLSX/CSV format"}, status=400)

            if model_name:
                try:
                    table_name = table_mappings.get(model_name)
                    field_names = get_tableFields(table_name)
                    column_names = df.columns.tolist()
                    print(column_names)
                    
                    try:
                        field_mapping = mappingFunc(column_names, field_names)
                    except Exception as e:
                        return JsonResponse({"error": f"Error mapping fields: {e}"}, status=500)
                    
                    print("OpenAI response: ", field_mapping)
                    print("Old DF: ", df)
                    df_new = df.rename(columns=field_mapping)
                    print("New DF: ", df_new)

                except Exception as e:
                    print(f"Error processing model_name: {e}")
                    return JsonResponse({"error": f"Error processing model_name: {e}"}, status=500)
            else:
                try:
                    file_name = os.path.splitext(xls_file.name)[0]
                    table_name = file_name.lower().replace(' ', '_')  # Ensure table name is lowercase and replace spaces with underscores
                except Exception as e:
                    print(f"Error processing file_name: {e}")
                    return JsonResponse({"error": f"Error processing file_name: {e}"}, status=500)
            df_new = df_new.to_json(orient="records")
            df_new_json = json.loads(df_new)
            print("New DF JSON type: ", type(df_new_json))
            bulk_upload_contacts.delay(df_new_json, tenant_id)

            return JsonResponse({"success": "Contacts are being uploaded"}, status = 200)
            
        except Exception as e:
            print(f"Unexpected error: {e}")
            return JsonResponse({"error": f"Unexpected error: {e}"}, status=500)
    else:
        return JsonResponse({"error": "Invalid request method"}, status=405)
