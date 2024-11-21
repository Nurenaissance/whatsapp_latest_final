import os
import json
from django.views.decorators.csrf import csrf_exempt
from django.http import JsonResponse
from .tables import get_db_connection, table_mappings
from openai import OpenAI
import pandas as pd
import numpy as np
import math
from contacts.models import Contact
from simplecrm.middleware import TenantMiddleware
from django.db import transaction, connection

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
                {"role": "system", "content": "You are a helpful assistant who answers STRICTLY to what is asked, based on the info provided. DO NOT ADD DATA FROM THE INTERNET. YOU KNOW NOTHING ELSE EXCEPT THE DATA BEING PROVIDED TO YOU. Keep your answers concise and only the required information"},
                {"role": "user", "content": f"Map these two lists with each other. List1: {list1_filtered}, List2: {list2_filtered}. Return only the mapped dictionary in JSON format. skip createdBy_id, tenant_id, bg_name, bg_id, isActive and createdOn. phone should be mandatorily mappped, dont map anything else if not sure"}
            ]
        )
        return response.choices[0].message.content
    except Exception as e:
        print(f"Error during mapping: {e}")
        raise

def reorder_df_columns_to_match_table(df, table_columns):
    """
    Reorders the columns of the DataFrame to match the order of the columns in the SQL table.
    """
    # Keep only the columns that exist in the SQL table and match the order
    ordered_columns = [col for col in table_columns if col in df.columns]
    # Reorder the DataFrame columns
    df_reordered = df[ordered_columns]
    print("reordered" ,df_reordered)
    return df_reordered

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
                    start = field_mapping.find('{')
                    end = field_mapping.find('}')
                    field_mapping = field_mapping[start:end + 1]
                    field_mapping_json = json.loads(field_mapping)
                    print(field_mapping_json.values())
                    df_new = df.rename(columns=field_mapping_json)

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
            
            timestamp_columns = ['createdOn', 'closedOn', 'interaction_datetime']  # List all your timestamp columns here
            for col in timestamp_columns:
                if col in df_new.columns:
                    df_new[col] = df_new[col].replace({np.nan: default_timestamp})
            
            boolean_columns = ['isActive']  # Add more columns here if needed
            for col in boolean_columns:
                if col in df_new.columns:
                    df_new[col] = df_new[col].replace({np.nan: False})  # First replace NaN values
                    df_new[col] = df_new[col].replace({1.0: True, 0.0: False})  # Then replace boolean values

            bigInt_columns = ['account_id', 'createdBy_id', 'name'] #Add columns  here to change value from nan to null (None)
            for col in bigInt_columns:
                if col in df_new.columns:
                    df_new[col] = df_new[col].replace({np.nan: None})

            try:
                # Get existing columns from the table and reorder DataFrame columns to match
                existing_columns = get_tableFields(table_name)
                df_new = reorder_df_columns_to_match_table(df_new, existing_columns)
                headers = [header for header in df_new.columns.tolist() if header.lower() != 'id']
                print("Filtered headers:", headers)
                
                df_new = df_new.loc[:, df_new.columns.str.lower() != 'id']
                data = df_new.values.tolist()
                print("Filtered data (first row):", data[0])
            except Exception as e:
                print(f"Error preparing data: {e}")
                return JsonResponse({"error": f"Error preparing data: {e}"}, status=500)

            column_definitions = ', '.join(f'"{header}" VARCHAR(255)' for header in headers)
            
            create_table_query = f"""
                CREATE TABLE IF NOT EXISTS "{table_name}" (
                    id SERIAL PRIMARY KEY,
                    {column_definitions},
                    "tenant_id" VARCHAR(255)
                );
            """

            conn = get_db_connection()
            cur = conn.cursor()
            
            try:
                cur.execute(create_table_query)
                conn.commit()
                print("Table created/found")
                skipped_rows =[]
                for row in data:
                    if table_name == 'contacts_contact':
                        values = list(row)

                        # Validate row data
                        if all(value in (None, '') or (isinstance(value, float) and math.isnan(value)) for value in values):
                            print(f"Skipping invalid row: {row}")
                            skipped_rows.append(row)
                            continue
                        
                        # Get phone number and validate
                        phone_index = headers.index('phone')  # Ensure 'phone' is in headers
                        phone = values[phone_index]
                        if not phone or not str(phone).strip():
                            print(f"Skipping row with empty or invalid phone: {row}")
                            skipped_rows.append(row)
                            continue

                        # Map values to model fields
                        data_dict = dict(zip(headers, values))
                        data_dict['tenant_id'] = tenant_id
                        print("Going Smooth")
                        try:
                            print(TenantMiddleware.current_tenant_id)
                            # connection = connections['default']
                            print("username and pw: ", connection.settings_dict['USER'], connection.settings_dict['PASSWORD'])
                            with transaction.atomic():
                                Contact.objects.create(**data_dict)
                                print(f"Row inserted successfully: {row}")
                        except Exception as e:
                            print(f"Error inserting data for row {row}: {e}")
                            skipped_rows.append(row)

                    else:
                        values = list(row) + [tenant_id]

                        # Check for invalid values (None or NaN) in the row before proceeding with insertion
                        if all(value is None or (isinstance(value, float) and math.isnan(value)) for value in values[:-1]):
                            print(f"Skipping invalid row: {row}")
                            continue  # Skip this row if it contains invalid data
                        # Check if phone number is empty or invalid
                        phone = values[3]  # Assuming the phone number is at index 2
                        if not phone or (isinstance(phone, str) and not phone.strip()):
                            print(f"Skipping row with empty or invalid phone: {row}")
                            continue  # Skip this row if phone number is empty or invalid

                        insert_query = f"""
                            INSERT INTO "{table_name}" ({', '.join(f'"{header}"' for header in headers)}, "tenant_id") 
                            VALUES ({', '.join('%s' for _ in range(len(headers)))}, %s);
                        """

                        print("Final Values: ", values)
                        print("Row: ", row)
                        
                        try:
                            cur.execute(insert_query, values)
                            print("Row inserted")
                            conn.commit()
                        except Exception as e:
                            print(f"Error inserting data: {e}")
                            conn.rollback()
                            continue  # Skip this row and continue with the next one

                return JsonResponse({"message": "XLS file uploaded and data inserted successfully", "table_name": table_name}, status=200)

            except Exception as e:
                conn.rollback()
                print(f"Error creating table: {e}")
                return JsonResponse({"error": f"Error creating table: {e}"}, status=500)

            finally:
                cur.close()
                conn.close()

        except Exception as e:
            print(f"Unexpected error: {e}")
            return JsonResponse({"error": f"Unexpected error: {e}"}, status=500)

    return JsonResponse({"error": "Invalid request method"}, status=405)
