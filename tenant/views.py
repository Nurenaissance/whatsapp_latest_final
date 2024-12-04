import json
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from .models import Tenant
from .serializers import TenantSerializer
from django.db import connection, transaction
from django.contrib.auth import password_validation
from django.contrib.auth.models import User
from django.conf import settings
from django.db import IntegrityError
from simplecrm import database_settings
from django.contrib.auth.hashers import check_password


@csrf_exempt
def create_tenant_role(tenant_id, password):
    try:
        with transaction.atomic():
            with connection.cursor() as cursor:
                cursor.execute(
                    "CREATE ROLE crm_tenant_%s WITH INHERIT LOGIN PASSWORD %s IN ROLE crm_tenant;",
                    [tenant_id, password]
                )
                cursor.execute(
                    "CREATE ROLE crm_tenant_%s_admin WITH INHERIT IN ROLE crm_tenant_%s;",
                    [tenant_id, tenant_id]
                )
                cursor.execute(
                    "CREATE ROLE crm_tenant_%s_employee WITH INHERIT IN ROLE crm_tenant_%s;",
                    [tenant_id, tenant_id]
                )
                cursor.execute(
                    "CREATE ROLE crm_tenant_%s_manager WITH INHERIT IN ROLE crm_tenant_%s;",
                    [tenant_id, tenant_id]
                )
                cursor.execute(
                    "GRANT CREATE, INSERT ON SCHEMA public TO crm_tenant_%s;",
                    [tenant_id]
                )
                cursor.execute(
                    "GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO crm_tenant_%s;",
                    [tenant_id]
                )
                cursor.execute(
                    "GRANT CREATEROLE TO crm_tenant_%s;",
                    [tenant_id]
                )

        # Example database settings configuration (customize as needed)
        database_settings = settings.get_database_settings(tenant_id, password)
        settings.DATABASES['default'] = database_settings

        print(f"Tenant role created successfully: {tenant_id}")
        return {"status": "success", "message": f"Tenant {tenant_id} created successfully."}
    except Exception as e:
        print(f"Error creating tenant role: {e}")
        return {"status": "error", "message": str(e)}


@csrf_exempt
def tenant_list(request):
    """
    View to retrieve a list of all tenants or create a new tenant.
    """
    if request.method == 'GET':
        tenants = Tenant.objects.all()
        serializer = TenantSerializer(tenants, many=True)
        return JsonResponse(serializer.data, safe=False)
    
    elif request.method == 'POST':
        data = json.loads(request.body)
        print("RCVD DATA: ", data)
        tenant_id = data.get('tenant_id')
        organization = data.get('organization')
        db_user_password = data.get('password')
        cursor = connection.cursor()
        try:
            print("begin", tenant_id, organization)
            
            tenant = Tenant.objects.create(id=tenant_id, organization=organization, db_user=f"crm_tenant_{tenant_id}", db_user_password=db_user_password)
            print(tenant)
            print("middle")

            cursor.execute("BEGIN")
            
            cursor.execute(f"CREATE ROLE crm_tenant_{tenant_id} INHERIT LOGIN PASSWORD '{db_user_password}' IN ROLE crm_tenant")
            cursor.execute(f"ALTER ROLE crm_tenant_{tenant_id} WITH CREATEROLE;")
            cursor.execute("COMMIT")
            
            print("end")
            return JsonResponse({'msg': 'Tenant registered successfully'})
        except IntegrityError as e:
            # Rollback the transaction if any error occurs
            if cursor:
                cursor.execute("ROLLBACK")
            print("error: ", str(e))
            return JsonResponse({'message': f'Error creating tenant: {str(e)}'}, status=500)
        except Exception as e:
            print("ERROR: ", str(e))
            return JsonResponse({'message': f'Error creating tenant: {str(e)}'}, status=500)
    
    else:
        return JsonResponse({'msg': 'Method not allowed'}, status=405)

@csrf_exempt
def tenant_detail(request, tenant_id):
    """
    View to retrieve details of a specific tenant by ID.
    """
    if request.method == 'GET':
        try:
            tenant = Tenant.objects.get(id=tenant_id)
            serializer = TenantSerializer(tenant)
            return JsonResponse(serializer.data)
        except Tenant.DoesNotExist:
            return JsonResponse({'msg': 'Tenant not found'}, status=404)
    else:
        return JsonResponse({'msg': 'Method not allowed'}, status=405)

@csrf_exempt
def add_catalog_id(request):
    if request.method != 'POST':
        return JsonResponse({'error': 'Invalid request method'}, status=405)
    
    try:
        tenant_id = request.headers.get('X-Tenant-Id')
        if not tenant_id:
            return JsonResponse({'error': 'Tenant ID not provided in headers'}, status=400)
        
        data = json.loads(request.body)
        catalog_id = data.get('catalog_id')
        if not catalog_id:
            return JsonResponse({'error': 'Catalog ID not provided in request body'}, status=400)

        tenant = Tenant.objects.get(id=tenant_id)
        tenant.catalog_id = catalog_id
        tenant.save()

        return JsonResponse({'message': 'Catalog ID updated successfully'}, status=200)
    
    except Tenant.DoesNotExist:
        return JsonResponse({'error': 'Tenant not found'}, status=404)
    
    except json.JSONDecodeError:
        return JsonResponse({'error': 'Invalid JSON in request body'}, status=400)
    
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)

@csrf_exempt
def verify_tenant(request):
    if request.method == 'POST':
        try:
            data = json.loads(request.body) 
            org = data.get('organisation')
            password = data.get('password')
            
            tenant = Tenant.objects.get(organization=org)
            
            if password == tenant.db_user_password:
                return JsonResponse({'success': True}, status=200)
            else:
                return JsonResponse({'success': False, 'message': 'Incorrect password'}, status=401)
        
        except Tenant.DoesNotExist:
            return JsonResponse({'success': False, 'message': 'Organization not found'}, status=404)
        
        except Exception as e:
            return JsonResponse({'success': False, 'message': str(e)}, status=500)
    else:
        return JsonResponse({'success': False, 'message': 'Invalid request method'}, status=405)
