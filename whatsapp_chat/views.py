from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
import json, requests
from dynamic_entities.views import create_dynamic_model
from django.db import DatabaseError, transaction
from dynamic_entities.views import DynamicModelListView
from django.db import connection
from .models import WhatsappTenantData
from .tasks import process_message_status
from rest_framework import generics
from tenant.models import Tenant
from django.utils import timezone
from node_temps.models import NodeTemplate
from django.forms.models import model_to_dict
from shop.models import Products
from helpers.tables import get_db_connection
from datetime import datetime, timedelta

def convert_flow(flow, tenant):
    fields = []
    if tenant.catalog_id != None:
        catalog_id = tenant.catalog_id
    try:
        print("Received flow: ", flow)
        node_blocks = flow['nodes']
        edges = flow['edges']

        nodes = []
        adjList = []
        id = 0
        for node_block in node_blocks:
            print("Processing Node Block: ", node_block)
            if node_block['type'] == "start":
                print("TEST")
                continue;
            
            if node_block['type'] == 'askQuestion':
                print("QUESTION")
                data = node_block['data']
                node = {
                    "oldIndex": node_block["id"],
                    "id": id,
                    "body": data['question'] or "Choose Option:"
                }
                delay = data.get('delay')
                if delay:
                    node['delay'] = delay

                if data['variable'] and data['dataType']: 
                    fields.append({
                        'field_name': data['variable'] or None,
                        'field_type': data['dataType'] or None
                    })
                    node['variable'] = data['variable']
                    node['variableType'] = data['variable']

                if data['optionType'] == 'Buttons':
                    node["type"] = "Button"
                    if data.get('med_id'):
                        node["mediaID"] = data['med_id']
                    print("Appending Node: ", node)
                    nodes.append(node)
                    list_id = id
                    id += 1
                    adjList.append([])
                     
                    for option in data['options']:
                        node = {
                            "id": id,
                            "body": option or "Choose Option:",
                            "type": "button_element"
                        }
                        print("Appending Node: ", node)
                        nodes.append(node)
                        adjList.append([])
                        adjList[list_id].append(id)
                        id += 1
                
                elif data['optionType'] == 'Text':
                    
                    node["type"] = "Text"
                    print("Appending Node: ", node)
                    nodes.append(node)
                    adjList.append([])
                    id += 1

                elif data['optionType'] == 'Lists':
                    node["type"] = "List"
                    print("Appending Node: ", node)
                    nodes.append(node)
                    list_id = id
                    id += 1
                    adjList.append([])
                    for option in data['options']:
                        node = {
                            "id": id,
                            "body": option or "Choose Option:",
                            "type": "list_element"
                        }
                        print("Appending Node: ", node)
                        nodes.append(node)
                        adjList.append([])
                        adjList[list_id].append(id)
                        id += 1

            elif node_block['type'] == 'sendMessage':
                print("MESSAGE")
                data = node_block['data']
                node = {
                    "oldIndex": node_block["id"],
                    "id": id,
                }
                delay = data.get('delay')
                if delay:
                    node['delay'] = delay
                content = data['fields']['content']
                type = data["fields"]['type']
                if type == "text":
                    node["type"] = "string"
                    node["body"] = content['text']
                elif type == "Image":
                    node["body"] = {"caption" :content["caption"], "id" : content["med_id"]} #"forget menu, would you like to eat this cute chameleon? its very tasty. trust me. you will forget other menu items once you taste our chamaleon delicacy." 
                    node["type"] = "image"
                    # node["body"]["id"] content["med_id"] #"https://letsenhance.io/static/8f5e523ee6b2479e26ecc91b9c25261e/1015f/MainAfter.jpg" #
                    # node["body"]["url"] = content["url"]
                elif type == "Location":
                    node["type"] = "location"
                    node["body"] = {
                        "latitude": content["latitude"],
                        "longitude": content["longitude"],
                        "name": content["loc_name"],
                        "address": content["address"]
                    }
                elif type == "Audio":
                    node["type"] = "audio"
                    node["body"] = {"audioID" : content["audioID"]}

                elif type == "Video":
                    node["type"] = "video"
                    node["body"] = {"videoID" : content["videoID"]}
                
                print("Appending Node: ", node)
                nodes.append(node)
                adjList.append([])
                id += 1

            elif node_block['type'] == 'setCondition':
                print("CONDITION")
                data = node_block['data']
                node = {
                    "oldIndex": node_block["id"],
                    "id": id,
                    "body": data['condition'],
                    "type": "Button"
                }
                delay = data.get('delay')
                if delay:
                    node['delay'] = delay
                
                print("Appending Node: ", node)
                nodes.append(node)
                adjList.append([])
                list_id = id
                id += 1
                node = {
                    "id": id,
                    "body": "Yes",
                    "type": "button_element"
                }
                
                print("Appending Node: ", node)
                nodes.append(node)
                adjList.append([])
                adjList[list_id].append(id)
                id += 1
                node = {
                    "id": id,
                    "body": "No",
                    "type": "button_element"
                }
                
                print("Appending Node: ", node)
                nodes.append(node)
                adjList.append([])
                adjList[list_id].append(id)
                id += 1

            elif node_block['type'] == 'ai':
                print("AI Mode")
                data = node_block['data']
                node = {
                    "oldIndex": node_block["id"],
                    "id": id,
                    "type": "AI",
                    "body": data['label']
                }
                delay = data.get('delay')
                if delay:
                    node['delay'] = delay
                
                print("Appending Node: ", node)
                nodes.append(node)
                adjList.append([])
                id += 1

            elif node_block['type'] == 'product':
                print("product")
                data = node_block['data']
                node = {
                    "oldIndex": node_block['id'],
                    "id": id,
                    "type": "product",
                    "catalog_id": catalog_id,
                    "product": data['product_ids']
                }

                delay = data.get('delay')
                if delay:
                    node['delay'] = delay

                if data.get('body'):
                    node['body'] = data.get('body')
                if data.get('footer'):
                    node['footer'] = data.get('footer')
                if data.get('head'):
                    node['head'] = data.get('head')
                  
                print("Appending Node: ", node)  
                nodes.append(node)
                adjList.append([])
                id += 1

            print("Processed Node Block: ", node)
        print("NODES: ", nodes)
        startNode = None
        for edge in edges:
            if edge['source'] == "start":
                startNodeIndex = int(edge['target'])
                print("start node index: ", startNodeIndex)
                for node in nodes:
                    if 'oldIndex' in node:
                        if int(node['oldIndex']) == startNodeIndex:
                            startNode = int(node['id'])
                print("updated start node: ", startNode)
            else:
                source = int(edge['source'])
                target = int(edge['target'])
                suffix = 0
                sourcehandle = edge['sourceHandle']
                if sourcehandle not in [None, "text"]:
                    if sourcehandle == "true":
                        suffix += 1
                    elif sourcehandle == "false":
                        suffix += 2
                    else:
                        suffix += int(sourcehandle[-1]) + 1
                
                for node in nodes:
                    if 'oldIndex' in node:
                        if int(node['oldIndex']) == source:
                            print("source")
                            n_source = int(node['id']) + suffix
                        if int(node['oldIndex']) == target:
                            print("target")
                            n_target = int(node['id'])
                print(f"source: {source}, target: {target}")
                adjList[n_source].append(n_target)

        for node in nodes:
            node.pop('oldIndex', None)
        print(f"fields: {fields}, start: {startNode}")
        return nodes, adjList, startNode, fields

    except Exception as e:
        print(f"An error occurred in convert flow: {e}")
        return None, None

@csrf_exempt
def insert_whatsapp_tenant_data(request):
    try:
        # Parse JSON data from the request body
        data = json.loads(request.body.decode('utf-8'))
        print("Received data at insert data: ", data)
        tenant_id = request.headers.get('X-Tenant-Id')
        if not tenant_id:
            return JsonResponse({'status': 'error', 'mesage': 'no tenant id found in headers'}, status = 400)
        tenant = Tenant.objects.get(id=tenant_id)

        business_phone_number_id = data.get('business_phone_number_id')
        access_token = data.get('access_token')
        account_id = data.get('accountID')
        firstInsertFlag = data.get('firstInsert', False)  # flag to mark the insert of bpid, access token, account id
        


        if firstInsertFlag:
            try:
                print("First insert")
                if not all([business_phone_number_id, access_token, account_id]):
                    return JsonResponse({'status': 'error', 'message': 'Missing required fields'}, status=400)

                # query = '''
                # INSERT INTO whatsapp_tenant_data (business_phone_number_id, access_token, account_id, tenant_id)
                # VALUES (%s, %s, %s, %s)
                # '''
                # #insert fallback msg and count
                
                # with connection.cursor() as cursor:
                #     print("Executing query:", query, business_phone_number_id, access_token, account_id, tenant_id)
                #     cursor.execute(query, [business_phone_number_id, access_token, account_id, tenant_id])
                #     connection.commit()  # Commit the transaction
                # print("Query executed successfully")
                # return JsonResponse({'message': 'Data inserted successfully'})


                whatsapp_data = WhatsappTenantData.objects.create(business_phone_number_id = business_phone_number_id, access_token = access_token, business_account_id = account_id, tenant = tenant)
                return JsonResponse({'status': 'success', 'bpid': whatsapp_data.business_phone_number_id})
                
            except Exception as e:
                print(f"An error occurred during first insert: {e}")
                return JsonResponse({'status': 'error', 'message': str(e)}, status=500)

        else:
            node_template_id = data.get('node_template_id')
            node_template = NodeTemplate.objects.get(id = node_template_id)
            node_data = node_template.node_data
            flow_name = node_template.name
            fallback_count = node_template.fallback_count
            fallback_message = node_template.fallback_msg
            if node_data is not None:
                try:
                    
                    print("Node Data: ", node_data)
                    flow_data, adj_list, start, dynamicModelFields = convert_flow(node_data, tenant)
                    
                    dynamicModelFields.append({
                                    'field_name': 'phone_no',
                                    'field_type': 'bigint'
                                })
                    flow_name = DynamicModelListView.sanitize_model_name(model_name=flow_name)
                    print("new flow name: ", flow_name)
                    model_name= flow_name
                    fields= dynamicModelFields
                    print("model name: ", model_name, fields)
                    create_dynamic_model(model_name=model_name, fields=fields,tenant_id=tenant_id)

                    #updating whatsapp_tenant_flow with flow_data and adj_list
                    # query = '''
                    # UPDATE whatsapp_tenant_data
                    # SET flow_data = %s, adj_list = %s, start = %s, fallback_message = %s, fallback_count = %s, flow_name = %s
                    # WHERE business_phone_number_id = %s
                    # '''
                    # print("adj listt: ", adj_list, flow_data, start)
                    # with connection.cursor() as cursor:
                    #     print("Executing query:", query, json.dumps(flow_data), json.dumps(adj_list), start, fallback_message, fallback_count, flow_name ,business_phone_number_id)
                    #     cursor.execute(query, [json.dumps(flow_data), json.dumps(adj_list), start, fallback_message, fallback_count, flow_name ,business_phone_number_id])
                    #     connection.commit()  # Commit the transaction

                    # return JsonResponse({'message': 'Data updated successfully'})
                    whatsapp_data = WhatsappTenantData.objects.filter(tenant_id = tenant_id)
                    whatsapp_data.update(
                        flow_data = flow_data,
                        adj_list = adj_list, 
                        start = start, 
                        fallback_count = fallback_count, 
                        fallback_message = fallback_message, 
                        flow_name = flow_name, 
                        updated_at = timezone.now()
                    )
                    print("Query executed successfully")
                    return JsonResponse({'status': 'success', 'message': 'data succesfully updated'})

                except Exception as e:
                    print(f"An error occurred during update: {e}")
                    return JsonResponse({'status': 'error', 'message': str(e)}, status=500)
            else:
                return JsonResponse({'message': 'No Node Data Present'}, status=400)
        
    except json.JSONDecodeError:
        return JsonResponse({'status': 'error', 'message': 'Invalid JSON'}, status=400)
    except Exception as e:
        print(f"An unexpected error occurred at insert whatsapptenant data: {e}")
        return JsonResponse({'status': 'error', 'message': str(e)}, status=500)    

@csrf_exempt
def get_whatsapp_tenant_data(request):
    try:
        tenant_id = request.headers.get('X-Tenant-Id') 
        bpid = request.headers.get('bpid')
        
        # Retrieve WhatsappTenantData for the specified tenant
        print("TENAND AND BID: ", tenant_id, bpid)
        whatsapp_data_json = {}
        if tenant_id:
            whatsapp_data = WhatsappTenantData.objects.get(tenant_id=tenant_id)
            whatsapp_data_json = model_to_dict(whatsapp_data)
        elif bpid:  
            whatsapp_data = WhatsappTenantData.objects.get(business_phone_number_id=bpid)
            tenant_id = whatsapp_data.tenant
            print("Tenantkokookko: ", tenant_id)
            whatsapp_data_json = model_to_dict(whatsapp_data)
            
        
        # Retrieve all Products associated with the specified tenant
        catalog_data = Products.objects.filter(tenant_id=tenant_id)
        catalog_data_json = list(catalog_data.values())  # Convert to a list of dictionaries
        
        # Print data for debugging
        print("data:", whatsapp_data_json, catalog_data_json)
        
        # Return data in a combined JSON response
        return JsonResponse({
            'whatsapp_data': whatsapp_data_json,
            'catalog_data': catalog_data_json
        }, safe=False)

    except DatabaseError as e:
        return JsonResponse({'error': 'Database error occurred', 'details': str(e)}, status=500)

    except Exception as e:
        print("Error occurred with tenant:", tenant_id)
        return JsonResponse({'error': 'An unexpected error occurred', 'details': str(e)}, status=500)


@csrf_exempt
def get_tenant(request):
    try:
        bpid = request.GET.get('bpid')
        if not bpid:
            print("no bpid---------------------------------")
            return JsonResponse({"error": "Missing 'bpid' parameter"}, status=400)
        
        whatsapp_data = WhatsappTenantData.objects.get(business_phone_number_id = bpid)
        res = whatsapp_data.tenant.id
        if res is None:
            print("no res---------------------------------")
            return JsonResponse({"error": f"No tenant found for bpid {bpid}"}, status=404)
        print("res----------------------", res)
        return JsonResponse({
            "tenant" : res
        })
    except Exception as e:
        print("Error in get_tenant: ", e)
        return JsonResponse({"error": "An error occurred while retrieving tenant", "details": str(e)}, status=500)

# @csrf_exempt
# def update_message_status(request):
#     try:
#         # Print the raw request body for debugging
#         # print("Received request:", request)
#         # print("Request body:", request.body.decode('utf-8'))
        
#         # Parse JSON data from the request body
#         data = json.loads(request.body)
#         tenant_id = request.headers.get('X-Tenant-Id')
#         print("tenant rcvd: ", tenant_id)
#         # print("Data Rcvd: ", data, tenant_id)
        
#         # Extract data from the JSON object
#         business_phone_number_id = data.get('business_phone_number_id')
#         isFailed = data.get('is_failed')
#         isReplied = data.get('is_replied')
#         isRead = data.get('is_read')
#         isDelivered = data.get('is_delivered')
#         isSent = data.get('is_sent')
#         phone_number = data.get('user_phone')
#         messageID = data.get('message_id')
#         broadcastGroup_id = data.get('bg_id')
#         broadcastGroup_name = data.get('bg_name')
#         template_name = data.get('template_name')
#         time = data.get('timestamp')
#         print("Time: ", time)

#         timestamp_seconds = time/ 1000

#         datetime_obj = datetime.fromtimestamp(timestamp_seconds)

#         # Format the datetime object as a string (PostgreSQL-compatible)
#         postgres_timestamp = datetime_obj.strftime('%Y-%m-%d %H:%M:%S')
        
#         with transaction.atomic():
#             with connection.cursor() as cursor:
#                 query = """
#                     INSERT INTO whatsapp_message_id (message_id, business_phone_number_id, sent, delivered, read, replied, failed, user_phone_number, broadcast_group, broadcast_group_name, template_name,tenant_id, last_seen)
#                     VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
#                     ON CONFLICT (message_id)
#                     DO UPDATE SET
#                         sent = EXCLUDED.sent,
#                         delivered = EXCLUDED.delivered,
#                         read = EXCLUDED.read,
#                         failed = EXCLUDED.failed,
#                         replied = EXCLUDED.replied,
#                         last_seen = EXCLUDED.last_seen;
#                 """
#                 cursor.execute(query, [messageID, business_phone_number_id, isSent, isDelivered, isRead, isReplied, isFailed, phone_number, broadcastGroup_id, broadcastGroup_name, template_name, tenant_id, postgres_timestamp])
#             print("updated status for message id: ", messageID)
#             print(f"isSent: {isSent}, isDeli: {isDelivered}, isRead: {isRead}, isReplied: {isReplied} ", )

#         return JsonResponse({'message': 'Data inserted successfully'})
#     except json.JSONDecodeError as e:
#         print("JSON decode error:", e)
#         return JsonResponse({'error': 'Invalid JSON format'}, status=400)
#     except Exception as e:
#         print("Exception:", e)
#         return JsonResponse({'error': str(e)}, status=500)

@csrf_exempt
def get_status(request):
    if request.method == 'GET':
        connection = get_db_connection()
        query = """
            SELECT *
            FROM whatsapp_message_id;
        """
        try:
            with connection.cursor() as cursor:
                cursor.execute(query)
                rows = cursor.fetchall()

            message_statuses = [
                {
                    "business_phone_number_id": row[0],
                    "is_sent": row[1],
                    "is_delivered": row[2],
                    "is_read": row[3],
                    "user_phone_number": row[4],
                    "message_id": row[5],
                    "broadcast_group": row[6],
                    "is_replied": row[7],
                    "is_failed": row[8]
                }
                for row in rows
            ]

            return JsonResponse({"message_statuses": message_statuses})

        except Exception as e:
            return JsonResponse({"error": f"An error occurred: {str(e)}"}, status=500)


def send_template(name):
    print(f"Preparing to send template: {name}")
    
    bg_id = None
    template = {
        "name": "basic_template"
    }
    business_phone_number_id = 241683569037594
    phone_numbers = [919548265904]

    data = {
        "template": template,
        "business_phone_number_id": business_phone_number_id,
        "phone_numbers": phone_numbers
    }

    url = "https://localhost:8080/send-template"
    response = requests.post(url, json=data)

    if response.status_code == 200:
        print("Template sent successfully!")
    else:
        print(f"Failed to send template. Status code: {response.status_code}")

def check_for_schedule(scheduler):
    today = datetime.now().date()
    print(f"Checking schedule for today: {today}")

    scheduled_event = {
        "name": "basic_template",
        "scheduled_time": datetime(today.year, today.month, today.day, 17, 44)
    }

    print(f"Scheduled event time: {scheduled_event['scheduled_time']}")

    if scheduled_event['scheduled_time'].date() == today:
        time_diff = scheduled_event['scheduled_time'] - datetime.now()
        print(f"Time difference to scheduled event: {time_diff}")
        
        if time_diff.total_seconds() > 0:
            print(f"Scheduling event at {scheduled_event['scheduled_time']}")
            scheduler.add_job(send_template, 'date', run_date=scheduled_event['scheduled_time'], args=[scheduled_event['name']])
            print("Message Sent")
        else:
            print("The scheduled event time has already passed today.")
    else:
        print("No event scheduled for today.")

import json
import logging
from datetime import datetime

from celery import shared_task
from django.db import transaction
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from contacts.models import Contact
# Configure logging
logger = logging.getLogger(__name__)

def convert_time(datetime_str):
    """
    Converts a date-time string from 'DD/MM/YYYY, HH:MM:SS.SSS'
    to PostgreSQL-compatible 'YYYY-MM-DD HH:MM:SS.SSS' format.
    
    Args:
        datetime_str (str): The date-time string to be converted.
    
    Returns:
        str: Converted date-time string in PostgreSQL format.
    """
    try:
        # Parse the input date-time string
        parsed_datetime = datetime.strptime(datetime_str, "%d/%m/%Y, %H:%M:%S.%f")
        # Convert it to the PostgreSQL-compatible format
        postgres_format = parsed_datetime.strftime("%Y-%m-%d %H:%M:%S.%f")
        return postgres_format
    except ValueError as e:
        print(f"Error converting datetime: {e}")
        return None
    

@csrf_exempt
@require_http_methods(["POST"])
def update_message_status(request):

    """
    View to queue message status updates for async processing
    
    :param request: HTTP request
    :return: JSON response with task status
    """
    try:
        try:
            data = json.loads(request.body)
        except json.JSONDecodeError:
            return JsonResponse({'error': 'Invalid JSON format'}, status=400)
        
        required_fields = ['message_id', 'timestamp']
        if not all(data.get(field) for field in required_fields):
            return JsonResponse({'error': 'Missing required fields'}, status=400)
        raw_time = data['timestamp']
        data['timestamp'] = convert_time(raw_time)
        
        message_payload = {
            'message_id': data.get('message_id'),
            'data': data,
            'tenant_id': request.headers.get('X-Tenant-Id')
        }

        # Enqueue the task
        print("Message Payload: ", message_payload)
        task_1 = process_message_status.delay(message_payload)
        # task_2 = process_new_set_status.delay(message_payload)

        return JsonResponse({
            'message': 'Status update queued', 
            'task1_id': task_1.id,
            # 'task2_id': task_2.id
        }, status=202)

    except Exception as e:
        logger.error(f"Unexpected error in set-status: {e}")
        return JsonResponse({'error': 'Internal server error'}, status=500)

def check_task_status(request, task_id):
    """
    Check the status of a queued task
    
    :param request: HTTP request
    :param task_id: ID of the Celery task
    :return: JSON response with task status
    """
    try:
        from celery.result import AsyncResult
        
        task_result = AsyncResult(task_id)
        
        return JsonResponse({
            "task_id": task_id,
            "status": task_result.status,
            "result": task_result.result
        })
    
    except Exception as e:
        logger.error(f"Error checking task status: {e}")
        return JsonResponse({"error": "Could not retrieve task status"}, status=500)

@csrf_exempt
def new_set_status(request):
    try:
        data = json.loads(request.body)
        print("data receieved in new set status: ", data)
        

        connection = get_db_connection()
        cursor = connection.cursor()

        
        message_id = data.get('message_id')
        template_name, bg_group = get_template_name(message_id)

        key = bg_group or template_name
        print("Key : ", key)
        update_fields = []
        flag_to_column = {
            'is_sent': 'sent',
            'is_delivered': 'delivered',
            'is_read': 'read',
            'is_replied': 'replied',
            'is_failed': 'failed'
        }

        for flag, column in flag_to_column.items():
            if data.get(flag) is True:
                print("Column found: ", column)
                update_fields.append(f"{column} = {column} + 1")

        cursor.execute(f"SELECT 1 FROM new_set_status WHERE name = %s;", (key,))
        row_exists = cursor.fetchone()

        if row_exists:
            print("Row Exists: ", key)
            if update_fields:

                update_query = f"UPDATE new_set_status SET {', '.join(update_fields)} WHERE name = %s;"
                cursor.execute(update_query, (key,))
                message = "Record updated successfully."
            else:
                message = "No updates were made as no flags were set to True."
        else:
            print("Row does not exist: ", key)
            tenant_id = request.headers.get('X-Tenant-Id') # Assuming tenant_id is passed in the request
            insert_query = """
            INSERT INTO new_set_status (name, tenant_id, sent, delivered, read, replied, failed)
            VALUES (%s, %s, 1, 0, 0, 0, 0);
            """
            cursor.execute(insert_query, (key, tenant_id))
            message = "New record created successfully."

        connection.commit()
        cursor.close()
        connection.close()

        return JsonResponse({"status": "success", "message": message}, status=200)

    except json.JSONDecodeError:
        return JsonResponse({"status": "error", "message": "Invalid JSON in request body."}, status=400)
    except KeyError as e:
        return JsonResponse({"status": "error", "message": f"Missing key in request data: {e}"}, status=400)
    except Exception as e:
        print("An exception occurred:", e)
        return JsonResponse({"status": "error", "message": "An internal server error occurred."}, status=500)


def process_new_set_status(payload):
    try:

        with transaction.atomic():
            message_id = payload['message_id']
            data = payload['data']
            tenant_id = payload['tenant_id']

        template_name, bg_group = get_template_name(message_id)

        key = bg_group or template_name
        print("Key : ", key)

        if key is None:
            return
        
        update_fields = []
        flag_to_column = {
            'is_sent': 'sent',
            'is_delivered': 'delivered',
            'is_read': 'read',
            'is_replied': 'replied',
            'is_failed': 'failed'
        }

        for flag, column in flag_to_column.items():
            if data.get(flag) is True:
                print("Column found: ", column)
                update_fields.append(f"{column} = {column} + 1")

    
        with connection.cursor() as cursor:
            cursor.execute(f"SELECT 1 FROM new_set_status WHERE name = %s;", (key,))
            row_exists = cursor.fetchone()

            if row_exists:
                print("Row Exists: ", key)
                if update_fields:

                    update_query = f"UPDATE new_set_status SET {', '.join(update_fields)} WHERE name = %s;"
                    cursor.execute(update_query, (key,))
                    message = "Record updated successfully."
                else:
                    message = "No updates were made as no flags were set to True."
            else:
                print("Row does not exist: ", key)
                insert_query = """
                INSERT INTO new_set_status (name, tenant_id, sent, delivered, read, replied, failed)
                VALUES (%s, %s, 1, 0, 0, 0, 0);
                """
                cursor.execute(insert_query, (key, tenant_id))
                message = "New record created successfully."

        print("Message: " ,message)
    except Exception as exc: 
        print("An Exception Occured in process_new_set_status: ", exc)


def get_template_name(message_id):
    print("rcvd message id: ", message_id)
    sql_query = """
    SELECT template_name, broadcast_group_name
    FROM whatsapp_message_id
    WHERE message_id = %s;
    """
    
    cursor = connection.cursor()
    cursor.execute(sql_query, (message_id,))
    
    result = cursor.fetchone()
    print("Result: ", result)
    if result:
        template_name, broadcast_group_name = result
        return template_name, broadcast_group_name
    else:
        return None, None
