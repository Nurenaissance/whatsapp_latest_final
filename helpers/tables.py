import psycopg2
from psycopg2.extras import RealDictCursor
from simplecrm.get_column_name import get_model_fields, get_column_mappings

table_mappings = {
    "Lead": "leads_lead",
    "Account": "accounts_account",
    "Contact": "contacts_contact",
    "Meeting": "interaction_meetings",
    "Call": "interaction_calls",
    "Opportunity" : "opportunities_opportunity",
    "Tasks" : "tasks_tasks",
    "Interaction" : "interaction_interaction",
    "Campaign" : "campaign_campaign",
    "Vendor" : "vendors_vendors",
    "Experience" : "product_experience"
}

def get_db_connection():
    return psycopg2.connect(
            dbname="nurenpostgres",
            user="nurenai",
            password="Biz1nurenWar*",
            host="nurenaistore.postgres.database.azure.com",
            port="5432"
        )


def fetch_table(table_name: str):
    try: 
        conn = get_db_connection()
        cur=conn.cursor(cursor_factory=RealDictCursor)

        cur.execute(f"SELECT * FROM {table_name}")
            
            # Fetch all rows from the executed query
        data = cur.fetchall()
            
            # Close the cursor and connection
        cur.close()
        conn.close()


        def format_row(row) -> str:
            ans="{" + "\n"
            ans+=",".join(f' "{key}": "{value}"' for key, value in row.items())
            ans+="\n" + "}"
            return ans

        # Iterate through each row and format
        formatted_rows = [format_row(row) for row in data]

        return formatted_rows
    
    except Exception as e:
        print(f"Error fetching data: {e}")
        return []

def get_tables_schema():
    query = """
        SELECT
            table_schema,
            table_name,
            column_name,
            ordinal_position,
            column_default,
            is_nullable,
            data_type,
            character_maximum_length,
            numeric_precision,
            numeric_scale,
            udt_name
        FROM
            information_schema.columns
        WHERE
            table_schema NOT IN ('information_schema', 'pg_catalog')
        ORDER BY
            table_schema,
            table_name,
            ordinal_position;
        """
    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        cursor.execute(query)
        table_struct = cursor.fetchall()

        table_schema = {}
        for row in table_struct:
            
            table_name =row[1]
            column_name = row[2]
            
            if table_name not in table_schema:
                table_schema[table_name] = []
            table_schema[table_name].append(column_name)

        result = [{table_name: columns} for table_name, columns in table_schema.items()]

        return result
    except Exception as error:
        print(f"Error fetching table schemas: {error}")
    finally:
        if conn:
            cursor.close()
            conn.close()


def upload_table(data_list: list, model_name: str, tenant_id):
    '''
    Function to upload data into tables in database. it maps the table columns with columns of preset tables and uploads it. uses chatGPT for mapping.

    Inputs: 
    data_list: list = list of rows of a  table with data_list[0] specifying the columns
    model_name: str = name of the table you would like to upload the data to. could be among [Lead, Account, Contact, Meeting, Call]

    '''
    print("model name: " ,model_name)
    columns = data_list[0]
    print("columns: " ,columns)
    fields = get_model_fields(model_name)
    print("model fields: " ,fields)
    mappings = get_column_mappings(fields, columns)
    print("mappings: " ,mappings)
    table_name = table_mappings.get(model_name)
    
    for index, item in enumerate(data_list[0]):
        if item in mappings.values():
            key_to_replace = next(key for key, value in mappings.items() if value == item)
            data_list[0][index] = key_to_replace
    print("table name: " ,table_name)
    column_names = [str(x) for x in data_list[0]]
    print("column list: " ,column_names)
    conn = get_db_connection()
    cur= conn.cursor()

    for row in data_list[1:]:
        values = list(row) + [tenant_id]  # Ensure row is a list and concatenate tenant_id
    
        insert_data_query = f"""
        INSERT INTO {table_name} ({', '.join(f'"{column}" ' for column in column_names)}, "tenant_id")
        VALUES ({', '.join('%s' for   _ in range(len(column_names)))}, %s);
        """
        cur.execute(insert_data_query, values)
        print("testingg")
        conn.commit()
    cur.execute(f"SELECT * FROM {table_name};")
    rows = cur.fetchall()
    print("\nData in the PostgreSQL table:")
    for row in rows:
        print(row)

    # Close the cursor and connection
    cur.close()
    conn.close()

def create_table(table_list: list, table_name: str):
    '''
    Function to upload data to a new table in database. It creates a new table with the table_name and uploads data into it.

    Inputs:
    table_list: list = list of rows of a  table with data_list[0] specifying the columns
    table_name: str = a text that you would like to be the table_name
    '''
    
    conn = get_db_connection()
    cur = conn.cursor()
    column_names = [str(x) for x in table_list[0]]
    print("columns : " ,column_names)
    create_table_query = f"""
        CREATE TABLE IF NOT EXISTS {table_name} (
        id SERIAL PRIMARY KEY,
        {', '.join(f'"{column}" VARCHAR(500)' for column in column_names)},
        "tenant_id" VARCHAR(255)
    );
    """
    cur.execute(create_table_query)
    conn.commit()
    print("test")
    for row in table_list[1:]:
        insert_data_query = f"""
        INSERT INTO {table_name} ({','.join(f'"{column}" ' for column in column_names)})
        VALUES ({','.join(f"'{entity}'" for entity in row)});
        """
        cur.execute(insert_data_query)
        conn.commit()
    
    print("test2")
    cur.execute(f"SELECT * FROM {table_name};")
    rows = cur.fetchall()
    print("\nData in the PostgreSQL table:")
    for row in rows:
        print(row)

    # Close the cursor and connection
    cur.close()
    conn.close()
