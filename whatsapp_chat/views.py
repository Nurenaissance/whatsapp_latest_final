from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
import json
from dynamic_entities.views import create_dynamic_model
from django.db import DatabaseError
from dynamic_entities.views import DynamicModelListView
from django.db import connection
from .models import WhatsappTenantData
from rest_framework import generics
from tenant.models import Tenant
from django.utils import timezone
from node_temps.models import NodeTemplate
from django.forms.models import model_to_dict

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
            if node_block['type'] == "start":
                print("TEST")
                continue;
            if node_block['type'] == 'askQuestion':
                print("QUESTION")
                data = node_block['data']
                node = {
                    "oldIndex": node_block["id"],
                    "id": id,
                    "body": data['question']
                }
                delay = data.get('delay')
                if delay:
                    node['delay'] = delay
                if data['variable'] and data['dataType']: 
                    fields.append({
                        'field_name': data['variable'],
                        'field_type': data['dataType']
                    })
                    node['variable'] = data['variable']
                    node['variableType'] = data['variable']

                if data['optionType'] == 'Buttons':
                    node["type"] = "Button"
                    if data.get('med_id'):
                        node["mediaID"] = data['med_id']
                    nodes.append(node)
                    list_id = id
                    id += 1
                    adjList.append([])
                    for option in data['options']:
                        node = {
                            "id": id,
                            "body": option,
                            "type": "button_element"
                        }
                        nodes.append(node)
                        adjList.append([])
                        adjList[list_id].append(id)
                        id += 1
                elif data['optionType'] == 'Text':
                    
                    node["type"] = "Text"
                    nodes.append(node)
                    adjList.append([])
                    id += 1

                elif data['optionType'] == 'Lists':
                    node["type"] = "List"
                    nodes.append(node)
                    list_id = id
                    id += 1
                    adjList.append([])
                    for option in data['options']:
                        node = {
                            "id": id,
                            "body": option,
                            "type": "list_element"
                        }
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
                nodes.append(node)
                adjList.append([])
                list_id = id
                id += 1
                node = {
                    "id": id,
                    "body": "Yes",
                    "type": "button_element"
                }
                nodes.append(node)
                adjList.append([])
                adjList[list_id].append(id)
                id += 1
                node = {
                    "id": id,
                    "body": "No",
                    "type": "button_element"
                }
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
                    "product": data['product_id']
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
                    
                nodes.append(node)
                adjList.append([])
                id += 1

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
                print(f"source: {n_source}, target: {n_target}")
                adjList[n_source].append(n_target)

        for node in nodes:
            node.pop('oldIndex', None)
        print(f"fields: {fields}, start: {startNode}")
        return nodes, adjList, startNode, fields

    except Exception as e:
        print(f"An error occurred: {e}")
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
                    # print("Query executed successfully")
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
        
        whatsapp_data = WhatsappTenantData.objects.get(tenant_id = tenant_id)
        data = model_to_dict(whatsapp_data)
        return JsonResponse(data, safe=False)

    except DatabaseError as e:
        return JsonResponse({'error': 'Database error occurred', 'details': str(e)}, status=500)

    except Exception as e:
        print("Error occured with tenant: ", tenant_id)
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
    
@csrf_exempt
def update_message_status(request):
    try:
        # Print the raw request body for debugging
        # print("Received request:", request)
        # print("Request body:", request.body.decode('utf-8'))
        
        # Parse JSON data from the request body
        data = json.loads(request.body)
        
        # Extract data from the JSON object
        business_phone_number_id = data.get('business_phone_number_id')
        isFailed = data.get('is_failed')
        isReplied = data.get('is_replied')
        isRead = data.get('is_read')
        isDelivered = data.get('is_delivered')
        isSent = data.get('is_sent')
        phone_number = data.get('user_phone')
        messageID = data.get('message_id')
        broadcastGroup_id = data.get('bg_id')

        
        with connection.cursor() as cursor:
            if broadcastGroup_id != None:
                query = "UPDATE whatsapp_message_id SET broadcast_group = %s WHERE message_id = %s"
                cursor.execute(query, [broadcastGroup_id, messageID])
                connection.commit()
            else:
                query = """
                    INSERT INTO whatsapp_message_id (message_id, business_phone_number_id, sent, delivered, read, replied, failed, user_phone_number, broadcast_group)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                    ON CONFLICT (message_id)
                    DO UPDATE SET
                        sent = EXCLUDED.sent,
                        delivered = EXCLUDED.delivered,
                        read = EXCLUDED.read,
                        failed = EXCLUDED.failed,
                        replied = EXCLUDED.replied;
                """

                cursor.execute(query, [messageID, business_phone_number_id, isSent, isDelivered, isRead, isReplied, isFailed, phone_number, broadcastGroup_id])
                connection.commit()
                print("updated status for message id: ", messageID)
                print(f"isSent: {isSent}, isDeli: {isDelivered}, isRead: {isRead}, isReplied: {isReplied} ", )

        return JsonResponse({'message': 'Data inserted successfully'})
    except json.JSONDecodeError as e:
        print("JSON decode error:", e)
        return JsonResponse({'error': 'Invalid JSON format'}, status=400)
    except Exception as e:
        print("Exception:", e)
        return JsonResponse({'error': str(e)}, status=500)

@csrf_exempt
def get_status(request):
    if request.method == 'GET':
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
