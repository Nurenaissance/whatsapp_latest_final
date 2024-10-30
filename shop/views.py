from django.shortcuts import render
from .models import Catalog
from .serializers import ShopSerializer
from rest_framework import generics, exceptions, response, status
from tenant.models import Tenant
from django.views.decorators.csrf import csrf_exempt
import json, re
from django.http import JsonResponse
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from .models import Catalog, Products
from decimal import Decimal
from tenant.models import Tenant
from django.core.serializers import serialize

@csrf_exempt
def create_spreadsheets(request):
    if request.method != 'POST':
        return JsonResponse({'error': 'Invalid HTTP method. Only POST is allowed.'}, status=status.HTTP_405_METHOD_NOT_ALLOWED)
    
    try:
        tenant_id = request.headers.get('X-Tenant-Id')
        products = Products.objects.filter(tenant_id = tenant_id)
        print(f"Found {products.count()} products in the Catalog.")

        products_json = json.loads(serialize('json', products))
        prod_list = []
        for product in products_json:
            prod_list.append(product["fields"])
        print("prod list: ", prod_list)
        
        tenant = Tenant.objects.get(id = tenant_id)

        if tenant.spreadsheet_link != None:

            return JsonResponse({
                'message': 'Spreadsheet created and made public.',
                'spreadsheet_url': tenant.spreadsheet_link,
                'products': prod_list
            }, status=status.HTTP_200_OK)

        else:
            print("Initializing Google Sheets API...")
            credentials = service_account.Credentials.from_service_account_file('avian-outrider-439510-p8-cf177254bb98.json')
            sheets_service = build('sheets', 'v4', credentials=credentials)
            drive_service = build('drive', 'v3', credentials=credentials)
            print("Google Sheets and Drive services created successfully.")

            print("Creating a new spreadsheet...")
            spreadsheet = {
                'properties': {
                    'title': f'Product Catalog for {tenant.organization}'
                }
            }
            spreadsheet = sheets_service.spreadsheets().create(body=spreadsheet, fields='spreadsheetId').execute()
            spreadsheet_id = spreadsheet.get('spreadsheetId')
            print('Spreadsheet ID: {0}'.format(spreadsheet_id))

            exclude_fields = ["id", "catalog", "tenant", "quantity"]
            fields = [field.name for field in Products._meta.fields if field.name not in exclude_fields]
            values = [fields]
            print(f"Header row: {fields}")
            for product in products:
                row = []
                for field in fields:
                    value = getattr(product, field)
                    if isinstance(value, Tenant):
                        row.append(str(value)) 
                    elif isinstance(value, Decimal):
                        row.append(float(value))
                    else:
                        row.append(value)
                values.append(row)
                print(f"Added row: {row}")
            print("Values 1: ", values)
            body = {
                'values': values
            }

            print("Updating the spreadsheet with values...")
            sheets_service.spreadsheets().values().update(
                spreadsheetId=spreadsheet_id,
                range='Sheet1!A1',
                valueInputOption='RAW',
                body=body
            ).execute()
            print("Spreadsheet updated successfully.")

            print("Making the spreadsheet public...")
            permission = {
                'type': 'anyone',
                'role': 'reader'
            }
            
            drive_service.permissions().create(
                fileId=spreadsheet_id,
                body=permission,
                fields='id'
            ).execute()
            print("Spreadsheet made public.")

            spreadsheet_url = f"https://docs.google.com/spreadsheets/d/{spreadsheet_id}/edit"
            
            try:
                tenant.spreadsheet_link = spreadsheet_url
                tenant.save()
            except Tenant.DoesNotExist:
                print(f"No WhatsappTenantData found for tenant_id {tenant_id}")
            except Exception as e:
                print(f"An error occurred: {e}")

            
            return JsonResponse({
                'message': 'Spreadsheet created and made public.',
                'spreadsheet_url': spreadsheet_url,
                'products': prod_list
            }, status=status.HTTP_201_CREATED)

    except HttpError as error:
        print(f"An error occurred: {error}")
        return JsonResponse({'error': 'An error occurred while creating the spreadsheet.'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    except Exception as e:
        print(f"An unexpected error occurred: {e}")
        return JsonResponse({'error': 'An unexpected error occurred.'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

class ShopListCreateAPIView(generics.ListCreateAPIView):
    queryset = Products.objects.all()
    serializer_class = ShopSerializer

    def get_queryset(self):
        tenant_id = self.request.headers.get('X-Tenant-Id')
        print(f"Tenant ID from headers: {tenant_id}")
        return Products.objects.filter(tenant_id=tenant_id)

    def create(self, request, *args, **kwargs):
        tenant_id = self.request.headers.get('X-Tenant-Id')
        print(f"Tenant ID from headers in create: {tenant_id}")

        try:
            tenant = Tenant.objects.get(id=tenant_id)
            spreadsheet_link = tenant.spreadsheet_link
            print(f"Tenant found: {tenant}")
        except Tenant.DoesNotExist:
            print("Tenant not found")
            raise exceptions.NotFound("Tenant not found.")

        data = request.data
        print(f"Data received: {data}")

        if isinstance(data, list):
            for index, item in enumerate(data):
                item['tenant'] = tenant.id
                print(f"Tenant ID added to item {index}: {item}")
            many = True
        else:
            data['tenant'] = tenant.id
            print(f"Tenant ID added to data: {data}")
            many = False

        valid_items = []
        invalid_items = []

        for item_data in data:
            print("Item Data: ", item_data)
            serializer = self.get_serializer(data=item_data)
            try:
                serializer.is_valid(raise_exception=True)
                print("Serializer is valid")
                self.perform_create(serializer)
                updated_item_data = {k:v for k,v in item_data.items() if k!= 'quantity'}
                print("UID: ", updated_item_data)
                update_spreadsheet("add", spreadsheet_link, "Sheet1", updated_item_data)
            except exceptions.ValidationError as e:
                errors = serializer.errors
                error_list = errors.get('product_id', [])
                for error in error_list:
                    if error.code == 'unique':
                        print("Item data to be updated: ", item_data)
                        update_existing(item_data)
                        updated_item_data = {k:v for k,v in item_data.items() if k!= 'quantity'}
                        print("UID: ", updated_item_data)
                        update_spreadsheet("update", spreadsheet_link, item_data['product_id'], updated_item_data)
                    else:
                        print(f"Validation error on item {item_data}: {serializer.errors}")
                continue
            except Exception as e:
                print(f"Unexpected error: {e}")
                continue

        print(valid_items, invalid_items)

        headers = self.get_success_headers(serializer.data)
        return response.Response(serializer.data, status=status.HTTP_201_CREATED, headers=headers)

@csrf_exempt
def process_order(request):
    try:
        data = json.loads(request.body)
        print("data: ", data)
        
        order = data.get('order', [])
        
        if not order:
            return JsonResponse({'error': 'No order data found'}, status=400)
        
        insufficient_quantity_errors = []
        querysets = []
        for product in order:
            try:
                product_id = product.get('id')
                quantity = product.get('quantity')
                
                if product_id is None or quantity is None:
                    return JsonResponse({'error': 'Product id or quantity is missing'}, status=400)
                
                queryset = Products.objects.get(product_id=product_id)
                
                if queryset.quantity < quantity:
                    insufficient_quantity_errors.append({
                        'product_id': product_id,
                        'requested_quantity': quantity,
                        'available_quantity': queryset.quantity
                    })
                else:
                    queryset.quantity -= quantity
                    querysets.append(queryset)

            except Products.DoesNotExist:
                return JsonResponse({'error': f'Product with id {product_id} not found'}, status=404)
            except ValueError:
                return JsonResponse({'error': 'Invalid quantity value'}, status=400)

        if insufficient_quantity_errors:
            return JsonResponse({
                'status': 'failure',
                'reason': 'insufficient_quantity',
                'insufficient_quantities': insufficient_quantity_errors
            }, status=200)
        
        else: 
            for queryset in querysets:
                queryset.save()

        return JsonResponse({'status': 'success', 'message': 'Order processed successfully'}, status=200)

    except json.JSONDecodeError:
        return JsonResponse({'error': 'Invalid JSON'}, status=400)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)

def update_existing(data_item):
    print("Data: ", data_item)

    fields = [
        'title', 'description', 'link', 'image_link',
        'condition', 'availability', 'price', 'brand', 'status'
    ]

    product_id = data_item['product_id']
    print(product_id)

    try:
        product = Products.objects.get(product_id=product_id)
        print("Product: ", product)

        # Check and update fields that are different
        for field in fields:
            if field in data_item:  # Check if the field exists in the data_item
                current_value = getattr(product, field, None)
                new_value = data_item[field]
                
                if current_value != new_value:  # Compare current value with new value
                    setattr(product, field, new_value)  # Update the product field
                    print(f"Updated {field}: {current_value} -> {new_value}")

        product.save() 
        print(f"Product with ID {product_id} updated successfully.")

    except Exception as e:
        print(f"Product with ID {product_id} does not exist.", str(e))
    # update spreadsheet
    # return response.Response(
    #     {"message": "Update completed"},
    #     status=status.HTTP_200_OK
    # )


def extract_spreadsheet_id(link):
    match = re.search(r'/d/([a-zA-Z0-9_-]+)', link)
    if match:
        return match.group(1)
    else:
        raise ValueError("Invalid Google Sheets Link")

def update_spreadsheet(mode, spreadsheet_link, range_name, values):
    print("Values: ", values)
    # Extract spreadsheet ID from the link
    spreadsheet_id = extract_spreadsheet_id(spreadsheet_link)
    print("id: ", spreadsheet_id)
    credentials = service_account.Credentials.from_service_account_file('avian-outrider-439510-p8-cf177254bb98.json')
    sheets_service = build('sheets', 'v4', credentials=credentials)
    
    
    #order is important
    data = [
        values['product_id'],
        values['title'],
        values['description'],
        values['link'],
        values['image_link'],
        values['condition'],
        values['availability'],
        values['price'],
        values['brand'],
        values['status']
    ]

    try:
        if mode == "add":
            sheets_service.spreadsheets().values().append(
                spreadsheetId=spreadsheet_id,
                range=range_name,
                valueInputOption='RAW',
                body={'values': [data[:-2]]}
            ).execute()
            print("Row added successfully.")

        elif mode == "update":
            product_id = range_name
            range_product_id = "Sheet1!A:A"
            result = sheets_service.spreadsheets().values().get(
                spreadsheetId = spreadsheet_id,
                range=range_product_id,
            ).execute()
            
            values = result.get('values', [])
            print("HHUHUSHBS: ", values)
                  
            for i, row in enumerate(values):
                if row[0] == product_id:
                    row_id = i+1
                    break
            
            sheets_service.spreadsheets().values().update(
                spreadsheetId=spreadsheet_id,
                range=f"Sheet1!A{row_id}:J{row_id}",
                valueInputOption='RAW',
                body={'values': [data[:-2]]}
            ).execute()
            print("Row updated successfully.")

    except HttpError as e:
        print(f"An HTTP error occurred: {e}")
    except Exception as e:
        print(f"An error occurred: {e}")

