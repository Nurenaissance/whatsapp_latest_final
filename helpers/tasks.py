
from celery import shared_task
from django.db import transaction
import logging
from django.http import JsonResponse
from .tables import get_db_connection
import numpy as np
import math, json, pandas as pd
from contacts.models import Contact
from simplecrm.middleware import TenantMiddleware
from django.db import transaction


logger = logging.getLogger(__name__)

default_timestamp = '1970-01-01 00:00:00'


@shared_task(bind=True, max_retries=3)
def upload_file_async(self, table_name, tenant_id, df_new):
    try:
        df_new = json.loads(df_new)
        df_new = pd.DataFrame(df_new)
        print("Type of df now: ", type(df_new))
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
                    # print("Going Smooth")
                    try:
                        print(TenantMiddleware.current_tenant_id)
                        # connection = connections['default']
                        # print("username and pw: ", connection.settings_dict['USER'], connection.settings_dict['PASSWORD'])
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
    except Exception as exc:
        logger.error(f"Error uploading: {exc}")
        # Retry with exponential backoff
        self.retry(exc=exc, countdown=2 ** self.request.retries)


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
