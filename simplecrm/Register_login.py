from django.contrib.auth.models import User
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
import json
from django.contrib.auth import authenticate
from .models import CustomUser
from tenant.models import Tenant 
from django.contrib.auth import logout
from django.db import connections
from django.db import connection, IntegrityError
import logging
logger = logging.getLogger(__name__)

@csrf_exempt
def register(request):
    if request.method == 'POST':
        data = json.loads(request.body)
        username = data.get('username')
        email = data.get('email')
        password = data.get('password')
        # role = data.get('role', CustomUser.EMPLOYEE)  # Default role to employee if not provided
        organization = data.get('organisation')
        tenant_name = data.get('tenant')
        role = CustomUser.ADMIN
        
        if not username:
            print("Missing field: username")
        if not email:
            print("Missing field: email")
        if not password:
            print("Missing field: password")
        if not organization:
            print("Missing field: organization")
        if not tenant_name:
            print("Missing field: tenant_name")
    
        if not (username and email and password and organization and tenant_name):
            print("One or more required fields are missing")
            return JsonResponse({'msg': 'Missing required fields'}, status=400)
        
        if CustomUser.objects.filter(username=username).exists():
            return JsonResponse({'msg': 'Username already exists'}, status=400)
        
        try:
            tenant = Tenant.objects.get(id=tenant_name)
        except Tenant.DoesNotExist:
            return JsonResponse({'msg': 'Specified tenant does not exist'}, status=400)
        
        # Create a new user with the specified role, organization, and tenant
        user = CustomUser.objects.create_user(username=username, email=email, password=password, role=role, organization=organization, tenant=tenant)

        # Create a corresponding PostgreSQL role for the userx``
        try:
            with connection.cursor() as cursor:
                
                sql_role_name = f"crm_tenant_{role}"
                
                cursor.execute(f"CREATE ROLE {username} WITH LOGIN PASSWORD %s IN ROLE {sql_role_name};", [password])
                cursor.execute(f"GRANT {sql_role_name} TO {username};")
                
        except IntegrityError as e:
            return JsonResponse({'msg': f'Error creating role: {str(e)}'}, status=500)
        except Exception as e:
            return JsonResponse({'msg': f'Unexpected error: {str(e)}'}, status=500)

        return JsonResponse({'msg': 'User registered successfully'})
    else:
        return JsonResponse({'msg': 'Method not allowed'}, status=405)



class LoginView(APIView):
    def post(self, request):
        data = request.data
        username = data.get('username')
        password = data.get('password')
        
        if not (username and password):
            return Response({'msg': 'Missing required fields'}, status=status.HTTP_400_BAD_REQUEST)
        
        # Authenticate user
        user = authenticate(username=username, password=password)
        print(user,"user logged in is")
        if user:
            # Check user's role and tenant
            role = user.role
            tenant_id = user.tenant.id  # Get the tenant ID associated with the user
            user_id = user.id  # Get the user ID of the logged-in user

            response_data = {
                'tenant_id': tenant_id,
                'user_id': user_id,
                'role': role
            }
            if role == CustomUser.ADMIN:
                # Show admin views
                response_data['msg'] = 'Login successful as admin'
            elif role == CustomUser.MANAGER:
                # Show manager views
                response_data['msg'] = 'Login successful as manager'
            else:
                # Show employee views
                response_data['msg'] = 'Login successful as employee'
            
            return Response(response_data, status=status.HTTP_200_OK)
        else:
            logger.error(f"Authentication failed for username: {username}")
            return Response({'msg': 'Invalid credentials'}, status=status.HTTP_401_UNAUTHORIZED)


class LogoutView(APIView):
    def post(self, request):
        # Log out the user
        logout(request)
        tenant_id = request.headers.get('X-Tenant-Id')
        print("logging out tenant ", tenant_id)
        # Reset the database connection to default superuser
        connection = connections['default']
        connection.settings_dict.update({
            'USER': 'nurenai',
            'PASSWORD': 'Biz1nurenWar*',
        })
        connection.close()
        connection.connect()
        logger.debug("Database connection reset to default superuser")
        
        return Response({'msg': 'Logout successful'}, status=status.HTTP_200_OK)