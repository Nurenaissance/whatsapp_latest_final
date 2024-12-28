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
Create a flow structure for a WhatsApp chatbot with the following specifications:

Node Types:

Statement Node: Delivers messages or information to the user.
Option Node: Provides buttons or lists for user interaction, allowing users to select one option from multiple choices.
Condition Node: Asks Yes/No questions (e.g., "Would you like to go back?"). These nodes expect binary responses (true/false).
Image Node:  Sends images with appropriate caption
Node Details:

Each node should include:
A unique id (integer, starting from 0).
A type field to specify its type (statement_node, option_node, or condition_node).
A content field containing the message or options and title(in case of options).
A position field with x and y coordinates to define its layout position on the canvas.



Edge Details:

Define the connections between nodes using edges, which include:
source: The ID of the source node. If the source is an Option Node, append an option letter (e.g., 2a, 3b.. and so on) to indicate the selected option. If the source is a Condition Node, append -true or -false to indicate the response.
target: The ID of the target node.
type: Specify whether the edge is based on:
option: For edges originating from buttons/lists.
condition: For edges originating from Yes/No conditions.
statement: For simple transitions between statement nodes.


Sample Format:

nodes: {nodes}
edges: {edges}

Output Format:

Nodes: Provide a JSON array of nodes, with each node containing:
id, type, content, and position (x, y).
Inlcude atleast two image nodes

Edges: Provide a JSON array of edges, with each edge containing:
source, target, type.

Instructions:
Include two or more image nodes.
ONLY GIVE THE JSON STRUCTURE
make connections/edges logical and with respect to the conversation flow
Flow cannot end on an option node.
All the options of a option node must connect to a node. They cannot remain unconnected, Same goes with condition Node.
Please follow logical connections, flow should be continuos and shouldnt break in between.
all the options of option node should point to some node. make appropriate edges

"""

OPENAI_RESPONSE = """
 ```json
{
  "nodes": [
    {"id": 0, "type": "statement_node", "content": "Welcome to Nuren AI Support! How can I assist you today?",
    {"id": 1, "type": "option_node", "content": {"options": ["WhatsApp Flow Builder", "Broadcast Message", "Schedule Message", "Chatbot", "Catalog Management", "API Integration"], "title": "Select a feature to learn more about:"},
    {"id": 2, "type": "statement_node", "content": "Our WhatsApp Flow Builder allows you to create custom flows for your chatbot.",
    {"id": 3, "type": "statement_node", "content": "Broadcast Message lets you send messages to multiple recipients at once.", 
    {"id": 4, "type": "statement_node", "content": "With Schedule Message, you can set up messages to be sent at a later time.",
    {"id": 5, "type": "statement_node", "content": "Chatbot functionality allows automated interactions with customers.",
    {"id": 6, "type": "statement_node", "content": "Catalog Management helps you organize and present your products effectively.", 
    {"id": 7, "type": "statement_node", "content": "API Integration allows you to connect with various systems for enhanced automation.",
    {"id": 8, "type": "condition_node", "content": "Would you like to learn more about another feature?", 
    {"id": 9, "type": "image_node", "caption": "Discover the power of automation with Nuren AI!",
    {"id": 10, "type": "image_node", "caption": "Here is how our chatbot automation works.",
    {"id": 11, "type": "statement_node", "content": "Thank you for using Nuren AI Support! Have a great day!",
  ],
  "edges": [
    {"source": "0", "target": "1", "type": "statement"},
    {"source": "1a", "target": "2", "type": "option"},
    {"source": "1b", "target": "3", "type": "option"},
    {"source": "1c", "target": "4", "type": "option"},
    {"source": "1d", "target": "5", "type": "option"},
    {"source": "1e", "target": "6", "type": "option"},
    {"source": "1f", "target": "7", "type": "option"},
    {"source": "2", "target": "8", "type": "statement"},
    {"source": "3", "target": "8", "type": "statement"},
    {"source": "4", "target": "8", "type": "statement"},
    {"source": "5", "target": "8", "type": "statement"},
    {"source": "6", "target": "10", "type": "statement"},
    {"source": "7", "target": "8", "type": "statement"},
    {"source": "8-true", "target": "1", "type": "condition"},
    {"source": "8-false", "target": "9", "type": "condition"},
    {"source": "10", "target": "11", "type": "statement"},
    {"source": "9", "target": "11", "type": "statement"}
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

            # Initialize the 'data' field properly
            modified_node['data'] = {'fields': {}, 'options': {}, 'question': {}, 'condition': {}, 'variable': {}}

            # Check the node type
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

                if len(options) <= 3:
                    modified_node['data']['optionType'] = "Buttons"

                elif len(options) > 3 and len(options) <= 10:
                    modified_node['data']['optionType'] = "Lists"
                

            elif node_type == "condition_node":
                modified_node['type'] = "setCondition"
                modified_node['data']['condition'] = node.get('content', {})
                prev_x = (prev_x + 400) % 2500
                prev_y = (prev_y - 900) % 700


                modified_node['position'] = {'x': prev_x, 'y': prev_y}

            elif node_type == "image_node":
                
                modified_node['type'] = "sendMessage"
                modified_node['data']['fields']['type'] = "Image"
                modified_node['data']['fields']['content'] = {'url': random.choice(sample_media_urls), 'med_id': random.choice(sample_media_ids), 'caption': node.get('caption', '')}
                prev_x = (prev_x + 400) % 2200
                modified_node['position'] = {'x': prev_x, 'y': prev_y}

            modified_nodes.append(modified_node)
        
        except KeyError as e:
            print(f"KeyError: Missing key {e} in node {node}")
        except Exception as e:
            print(f"Error processing node {node}: {e}")
    
    modified_edges = [start_edge]
    for edge in edges:
        try:
            source = str(edge.get('source', ''))
            target = str(edge.get('target', ''))
            modified_edge = {
                'id': f"reactflow__edge-{source[0]}-{target}",
                'type': "smoothstep",
                'source': str(source[0]),
                'target': target,
                'animated': True,
                'targetHandle': None
            }

            edge_type = edge.get('type', '')
            if edge_type == "option":
                option = source[-1]
                sourceHandle = f"option-{ord(option)-97}"
                print("Option: ", ord(option))

                modified_edge['sourceHandle'] = sourceHandle
            elif edge_type == "condition":
                boolean_value = source.split('-')[1] if '-' in source else ''
                modified_edge['sourceHandle'] = boolean_value.lower()
            else:
                modified_edge['sourceHandle'] = None

            modified_edges.append(modified_edge)

        except KeyError as e:
            print(f"KeyError: Missing key {e} in edge {edge}")
        except Exception as e:
            print(f"Error processing edge {edge}: {e}")

    print("Edges formed: ", modified_edges)
    print("Nodes Formed: ", modified_nodes)

    return {'edges': modified_edges, 'nodes': modified_nodes}

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
            model="gpt-4o-mini",
            messages=[
                {"role": "developer", "content": OPENAI_prompt},
                {"role": "assistant", "content": OPENAI_RESPONSE},
                {"role": "user", "content": MODIFIED_PROMPT}
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