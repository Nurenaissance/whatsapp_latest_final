import psycopg2, random
from psycopg2.extras import RealDictCursor
from django.views.decorators.csrf import csrf_exempt
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
            dbname="nurenpostgres_Whatsapp",
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

from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
import psycopg2

@csrf_exempt
def delete_tenant(request):
    if request.method != "POST":
        return JsonResponse({"error": "Invalid HTTP method. Only POST is allowed."}, status=405)

    try:
        # Parse the incoming request data
        data = request.json()
        tenant_id = data.get('tenant')

        if not tenant_id:
            return JsonResponse({"error": "Tenant ID is required."}, status=400)

        # Establish database connection
        connection = get_db_connection()
        cur = connection.cursor()

        # Execute the deletion query
        query = f"""
        DELETE FROM contacts_contact WHERE tenant_id = %s;
        DELETE FROM simplecrm_customuser WHERE tenant_id = %s;
        DELETE FROM tenant_tenant WHERE id = %s;
        """
        cur.execute(query, (tenant_id, tenant_id, tenant_id))

        # Commit changes
        connection.commit()

        cur.close()
        connection.close()

        return JsonResponse({"success": f"Tenant {tenant_id} and related data deleted successfully."}, status=200)

    except psycopg2.Error as e:
        # Handle database-specific errors
        return JsonResponse({"error": "Database error occurred.", "details": str(e)}, status=500)

    except Exception as e:
        # Handle general exceptions
        return JsonResponse({"error": "An unexpected error occurred.", "details": str(e)}, status=500)

    finally:
        # Ensure the connection is closed even if an exception occurs
        if 'cur' in locals() and not cur.closed:
            cur.close()
        if 'connection' in locals() and connection:
            connection.close()

start_edge = {
    'id': "start-edge",
    'source': "start",
    'target': "0"
}

normal_edge = {
    'id': f"reactflow__edge-SOURCE_NODE-TARGET_NODE",
    'type': "smoothstep",
    'source': "SOURCE_NODE", # id of the source node
    'target': "TARGET_NODE", # id of the target node
    'animated': True,
    'sourceHandle': None,
    'targetHandle': None
}

setCondition_edge = {
    'id': f"reactflow__edge-SOURCE_NODE-TARGET_NODE",
    'type': "smoothstep",
    'source': "SOURCE_NODE", # id of the source node
    'target': "TARGET_NODE", # id of the target node
    'animated': True,
    'sourceHandle': True or False, #depending on from which of the point it emerges
    'targetHandle': None
}

askQuestion_edge = {
    'id': f"reactflow__edge-SOURCE_NODE-TARGET_NODE",
    'type': "smoothstep",
    'source': "SOURCE_NODE", # id of the source node
    'target': "TARGET_NODE", # id of the target node
    'animated': True,
    'sourceHandle': "OPTION-NO", # option no of Buttons or Lists message
    'targetHandle': None
}

start_node = {
    'id': "start",
    'data': {
        'label': "Start"
    },
    'type': "start",
    'position': {
        'x': 0,
        'y': 0
    }
}

sendMessage_node = {
    'id': "ID IN INT",
    'data': {
        'fields': {
            'type': "text" or "Image",
            'content': {
                'text': "HERE GOES THE TEXT", #in case of type: text,

                'url': "HERE GOES THE URL FOR IMAGE", #in case of type: image,
                'med_id': "HERE GOES MEDIA ID(META)", #in case of type: image,
                'caption': "HERE GOES CAPTION FOR MEDIA", #in case of type: image
            }
        }
    },
    'type': "sendMessage",
    'position': {
        'x': "HERE GOES X_COORDINATE",
        'y': "HERE GOES Y_COORDINATE"
    }
}

askQuestion_node = {
    'id': "ID IN INT",
    'data': {
        'options': [
            "Option 1",
            "Option 2",
            "Option 3"
        ],
        'dataType': "HERE GOES THE DATA TYPE FOR THE VARIABLE", # in case of optionType: Text
        'question': "HERE GOES THE TEXT", # message text
        'variable': "HERE GOES THE VARIABLE", # in case of storing input like  name, address, etc (optionType: Text)
        'optionType': "Buttons" # Other option type includes: Buttons, List, Text
    },
    'type': "askQuestion",
    'position': {
        'x': "HERE GOES X_COORDINATE",
        'y': "HERE GOES Y_COORDINATE"
    }
}

setCondition_node = {
    'id': "ID IN INT",
    'data': {
        'condition': "HERE GOES THE TEXT", # message text
    },
    'type': "setCondition",
    'position': {
        'x': "HERE GOES X_COORDINATE",
        'y': "HERE GOES Y_COORDINATE"
    }
}


nodes = [
    {
    "id": "3",
    "type": "option_node",
    "content": {
        "options": ["Pizza", "Burger", "Pasta"],
        "title": "Select an item from our menu"
    },
    },
    {
    "id": "5",
    "type": "statement_node",
    "content": "Your order has been placed successfully! Would you like to do anything else?",
    },
    {
    "id": "6",
    "type": "condition_node",
    "content": "Would you like to go back to the main menu?",
    },
    {
    "id": "8",
    "type": "image_node",
    "caption": "Here is a beautiful image",
    },

]

sample_media_ids = ['1321497715645534', '463574016472484', '537678019423040', '1522303899162447', '1120339625617178']
sample_media_urls = [
    'https://pdffornurenai.blob.core.windows.net/pdf/image_1321497715645534?sv=2022-11-02&ss=bfqt&srt=co&sp=rwdlacupiytfx&se=2025-06-01T16:13:31Z&st=2024-06-01T08:13:31Z&spr=https&sig=8s7IAdQ3%2B7zneCVJcKw8o98wjXa12VnKNdylgv02Udk%3D',
    'https://pdffornurenai.blob.core.windows.net/pdf/image_463574016472484?sv=2022-11-02&ss=bfqt&srt=co&sp=rwdlacupiytfx&se=2025-06-01T16:13:31Z&st=2024-06-01T08:13:31Z&spr=https&sig=8s7IAdQ3%2B7zneCVJcKw8o98wjXa12VnKNdylgv02Udk%3D',
    'https://pdffornurenai.blob.core.windows.net/pdf/image_537678019423040?sv=2022-11-02&ss=bfqt&srt=co&sp=rwdlacupiytfx&se=2025-06-01T16:13:31Z&st=2024-06-01T08:13:31Z&spr=https&sig=8s7IAdQ3%2B7zneCVJcKw8o98wjXa12VnKNdylgv02Udk%3D',
    'https://pdffornurenai.blob.core.windows.net/pdf/image_1522303899162447?sv=2022-11-02&ss=bfqt&srt=co&sp=rwdlacupiytfx&se=2025-06-01T16:13:31Z&st=2024-06-01T08:13:31Z&spr=https&sig=8s7IAdQ3%2B7zneCVJcKw8o98wjXa12VnKNdylgv02Udk%3D',
    'https://pdffornurenai.blob.core.windows.net/pdf/image_1120339625617178?sv=2022-11-02&ss=bfqt&srt=co&sp=rwdlacupiytfx&se=2025-06-01T16:13:31Z&st=2024-06-01T08:13:31Z&spr=https&sig=8s7IAdQ3%2B7zneCVJcKw8o98wjXa12VnKNdylgv02Udk%3D'
]

edges = [
    { "source": "1", "target": 2, "type": "statement" },

    { "source": "2a", "target": 3,"type": "option" },
    { "source": "2b", "target": 7, "type": "option" },
    { "source": "2c", "target": 8,  "type": "option" },
    

    { "source": "4-true", "target": 5,  "type": "condition" },
    { "source": "4-false", "target": 3, "type": "condition" }
]


OPENAI_prompt = f"""
**Chatbot Flow Generation Instructions**

**Objective**: Create a structured WhatsApp chatbot flow with strict JSON formatting and logical connections.

**Node Requirements**:
1. Types:
   - `statement_node`: Information messages (required as first node)
   - `option_node`: Multiple-choice interactions (minimum 2 options)
   - `condition_node`: Yes/No questions
   - `image_node`: Images with caption (minimum 2 required)

2. Node Specifications:
   - Unique integer IDs starting from 0
   - Content structure:
     - Option: {{
       "title": "≤20 chars", 
       "options": ["≤20 chars", ...]
     }}
     - Condition: Yes/No question text (≤30 characters)

**Edge Requirements**:
1. Connection Rules:
   - Option Nodes: One edge per option (format: "{{id}}a", "{{id}}b", etc.)
   - Condition Nodes: Two edges ("{{id}}-true", "{{id}}-false")
   - Statement Nodes: Single outgoing edge
   - Image Nodes: Must connect to subsequent nodes

2. Flow Constraints:
   - Must start with statement_node (id=0)
   - Must end with statement_node
   - No circular dependencies in main flow
   - All leaf nodes must terminate at final statement

**Output Format**:
{{
  "nodes": [
    {{"id": 0, "type": "statement_node", "content": "...", "position": {{"x": 0, "y": 0}}}},
    {{"id": 1, "type": "option_node", "content": {{"title": "...", "options": [...]}}, "position": {{"x": 100, "y": 100}}}},
    {{"id": 2, "type": "image_node", "content": "caption...", "position": {{"x": 200, "y": 200}}}}
  ],
  "edges": [
    {{"source": "0", "target": "1", "type": "statement"}},
    {{"source": "1a", "target": "2", "type": "option"}}
  ]
}}

**Strict Validation Rules**:
1. Schema Compliance:
   - All node IDs must be sequential integers
   - Position coordinates > 0
   - Minimum 2 image nodes

2. Content Validation:
   - Button/list titles ≤20 characters
   - Option values ≤20 characters
   - Statement messages ≤40 characters
   - Condition questions ≤30 characters
   - No markdown formatting
   - Company name appears in first message
   - Industry-specific terminology

3. Flow Validation:
   - No orphaned nodes
   - All options/conditions must connect
   - Final node must be statement_node
   - No duplicate edges
"""
VALIDATION_PROMPT = """
**Validation Checklist**:

1. Structural Integrity:
   - Verify nodes[0].type == 'statement_node'
   - Confirm node count matches request parameter
   - Check all required node types present

2. Content Validation:
   - Button/list titles ≤20 chars (count: $title_length)
   - Option values ≤20 chars (check each option)
   - Company name in opening message
   - Image captions non-empty

3. Connection Validation:
   - All options have corresponding edges
   - Condition nodes have both true/false paths
   - Final node has no outgoing edges

4. JSON Validation:
   - Validate proper JSON syntax
   - Check for missing commas/braces
   - Ensure proper escaping

**Error Handling**:
If validation fails:
1. Reject with: "Validation failed: [specific reason]"
2. Show exact character counts for violations
3. Provide JSON path to error
4. Never return partial/invalid JSON
Example error: 
"Option node 1.title: 22/20 characters (trim 2)"
"Option node 3.options[0]: 23/20 characters"
"""

OPENAI_RESPONSE = """
{
  "nodes": [
    {"id": 0, "type": "statement_node", "content": "Welcome to XYZ Corp! How can we assist you today?", "position": {"x": 0, "y": 0}},
    {"id": 1, "type": "option_node", "content": {"title": "Main Menu", "options": ["Products", "Support", "Account"]}, "position": {"x": 150, "y": 50}},
    {"id": 2, "type": "image_node", "content": "Our product lineup", "position": {"x": 300, "y": 100}},
    {"id": 3, "type": "condition_node", "content": "Need more assistance?", "position": {"x": 450, "y": 150}}
  ],
  "edges": [
    {"source": "0", "target": "1", "type": "statement"},
    {"source": "1a", "target": "2", "type": "option"},
    {"source": "1b", "target": "3", "type": "option"},
    {"source": "3-true", "target": "1", "type": "condition"},
    {"source": "3-false", "target": "4", "type": "condition"},
    {"source": "2", "target": "4", "type": "statement"},
    {"id": 4, "type": "statement_node", "content": "Thank you for contacting XYZ Corp!", "position": {"x": 600, "y": 200}}
  ]
}
"""
def auto_place_nodes(nodes, start_x=100, start_y=100, x_gap=200, y_gap=150):
    """
    Automatically places nodes on a canvas-like structure.
    
    Args:
        nodes (list): List of nodes with id and type fields.
        start_x (int): Starting X coordinate for positioning.
        start_y (int): Starting Y coordinate for positioning.
        x_gap (int): Horizontal gap between nodes.
        y_gap (int): Vertical gap between nodes.
        
    Returns:
        list: Updated list of nodes with position fields (x, y).
    """
    current_x = start_x
    current_y = start_y
    type_rows = {}  # Store rows of nodes by type for better visual grouping

    # Categorize nodes by type
    for node in nodes:
        node_type = node['type']
        if node_type not in type_rows:
            type_rows[node_type] = []
        type_rows[node_type].append(node)
    
    # Place nodes row by row based on type
    for node_type, type_nodes in type_rows.items():
        for node in type_nodes:
            node['position'] = {"x": current_x, "y": current_y}
            current_x += x_gap
        current_x = start_x  # Reset x position for the next row
        current_y += y_gap   # Move to the next row

    return nodes


def makeFlow(nodes, edges):
    modified_nodes = []
    prev_x = 0
    prev_y = 0
    for node in nodes:
        try:
            modified_node = {}
            modified_node['id'] = str(node['id'])
            modified_node['data'] = {'fields': {}, 'options': {}, 'question': {}, 'condition': {}, 'variable': {}}

            node_type = node.get('type', '')
            if node_type == "statement_node":
                modified_node['type'] = "sendMessage"
                modified_node['data']['fields']['type'] = "text"
                modified_node['data']['fields']['content'] = {'text': node.get('content', '')}
                prev_x = (prev_x + 400) % 2200
                modified_node['position'] = {'x': prev_x, 'y': prev_y}

            elif node_type == "option_node":
                modified_node['type'] = "askQuestion"
                options = node.get('content', {}).get('options', [])
                modified_node['data']['options'] = options
                modified_node['data']['question'] = node.get('content', {}).get('title', '')
                prev_x = (prev_x + 300) % 1900
                prev_y = (prev_y + 600) % 700
                modified_node['position'] = {'x': prev_x, 'y': prev_y}
                modified_node['data']['optionType'] = "Buttons" if len(options) <= 3 else "Lists"

            elif node_type == "condition_node":
                modified_node['type'] = "setCondition"
                modified_node['data']['condition'] = node.get('content', '')
                prev_x = (prev_x + 400) % 2500
                prev_y = (prev_y - 900) % 700
                modified_node['position'] = {'x': prev_x, 'y': prev_y}

            elif node_type == "image_node":
                modified_node['type'] = "sendMessage"
                modified_node['data']['fields']['type'] = "Image"
                modified_node['data']['fields']['content'] = {
                    'url': random.choice(sample_media_urls),
                    'med_id': random.choice(sample_media_ids),
                    'caption': node.get('content', '')
                }
                prev_x = (prev_x + 400) % 2200
                modified_node['position'] = {'x': prev_x, 'y': prev_y}

            modified_nodes.append(modified_node)
        
        except KeyError as e:
            print(f"KeyError: {e} in node {node}")
        except Exception as e:
            print(f"Error processing node {node}: {e}")
    
    modified_edges = [{
        'id': 'start-edge',
        'source': 'start',
        'target': '0',
        'type': 'smoothstep',
        'animated': True
    }]

    for edge in edges:
        try:
            source_str = str(edge.get('source', ''))
            target_str = str(edge.get('target', ''))

            # Parse node ID and suffix from source
            node_id = ''.join(filter(str.isdigit, source_str))
            suffix = source_str[len(node_id):] if node_id else source_str

            modified_edge = {
                'id': f"reactflow__edge-{source_str}-{target_str}",
                'type': "smoothstep",
                'source': node_id,
                'target': target_str,
                'animated': True,
                'targetHandle': None
            }

            edge_type = edge.get('type', '')
            if edge_type == "option" and suffix:
                option_index = ord(suffix.lower()) - ord('a')
                modified_edge['sourceHandle'] = f"option-{option_index}"
            elif edge_type == "condition" and '-' in source_str:
                condition = source_str.split('-')[-1]
                modified_edge['sourceHandle'] = condition.lower()
            else:
                modified_edge['sourceHandle'] = None

            modified_edges.append(modified_edge)

        except Exception as e:
            print(f"Error processing edge {edge}: {e}")

    return {'nodes': modified_nodes, 'edges': modified_edges}
import json
import json
from django.views.decorators.csrf import csrf_exempt
from django.http import JsonResponse
import os
from openai import OpenAI

@csrf_exempt
def test(request):
    try:
    
            OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
            client = OpenAI(api_key=OPENAI_API_KEY)

            data = json.loads(request.body)
            prompt = data.get('prompt')
            nodes_count = data.get('nodes')
            industry = data.get('industry')
            company_name = data.get('company_name')
            prompt_data = data.get('data')

            MODIFIED_PROMPT = f"""
            Prompt: {prompt},
            Number of Nodes in flow: {nodes_count},
            Related to:  {industry} Industry,
            use Company Name: {company_name},
            Use this data wherever required: {prompt_data}
            """

            response = client.chat.completions.create(
                model="gpt-4o",
                messages=[
                     {
        "role": "system",
        "content": "You are a strict JSON validator. Follow these steps:\n1. Generate initial structure\n2. Validate against rules\n3. Either return valid JSON or error"
    },
                    {"role": "developer", "content": OPENAI_prompt},
                    {"role": "assistant", "content": OPENAI_RESPONSE},
                    {"role": "user", "content": MODIFIED_PROMPT},
                    {"role": "system" , "content": VALIDATION_PROMPT }
                ]
            )
            result = response.choices[0].message.content
    except Exception as e:
        print(f"Error during mapping: {e}")
        raise

    print("Raw Response: ", result)

    try:
        start = result.find('{')
        end = result.rfind('}')
        result = result[start:end + 1]
        # print("Result: ", result)
        result_json = json.loads(result)
        print(result_json)
        nodes = result_json['nodes']
        edges = result_json['edges']
        print(f"Nodes: {nodes}, Edges: {edges}")
        # Generate the flow
        flow = makeFlow(nodes, edges)
        # Convert the flow dictionary to JSON
        flow_json = json.dumps(flow)

        return JsonResponse({"success": True, "data": flow}, status = 200)
    except Exception as e:
        print("An exception occured: ", e)
        return JsonResponse({"error": str(e)}, status=400)


    # # SQL query to update the row where name is 'Road'
    # sql_query = "UPDATE node_temps_nodetemplate SET node_data = %s WHERE name = %s;"
 
    # try:
    #     # Connect to the database
    #     conn = get_db_connection()
    #     cursor = conn.cursor()

    #     # Execute the query with parameters
    #     cursor.execute(sql_query, (flow_json, "Road"))
    #     conn.commit()

    #     return JsonResponse({"status": "success", "message": "Flow updated successfully!"})

    # except Exception as e:
    #     print("An exception occured: ", e)
    #     return JsonResponse({"status": "error", "message": str(e)})

    # finally:
    #     if cursor:
    #         cursor.close()
    #     if conn:
    #         conn.close()