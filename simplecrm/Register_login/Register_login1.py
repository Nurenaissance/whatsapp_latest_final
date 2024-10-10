from django.contrib.auth.models import User
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
import json
from django.contrib.auth import authenticate
from ..models import CustomUser
from tenant.models import Tenant 
from django.contrib.auth import logout
from django.db import connections
from django.db import connection
import logging
logger = logging.getLogger(__name__)

@csrf_exempt
@csrf_exempt
def register(request):
    if request.method == 'POST':
        data = json.loads(request.body)
        username = data.get('username')
        email = data.get('email')
        password = data.get('password')
        role = data.get('role', CustomUser.EMPLOYEE)  # Default role to employee if not provided
        organization = data.get('organization')
        tenant_name = data.get('tenant')
        
        if not (username and email and password and organization and tenant_name):
            return JsonResponse({'msg': 'Missing required fields'}, status=400)
        
        if CustomUser.objects.filter(username=username).exists() or CustomUser.objects.filter(email=email).exists():
            return JsonResponse({'msg': 'Username or email already exists'}, status=400)
        
        try:
            tenant = Tenant.objects.get(id=tenant_name)
        except Tenant.DoesNotExist:
            return JsonResponse({'msg': 'Specified tenant does not exist'}, status=400)
        
        # Create a new user with the specified role, organization, and tenant
        user = CustomUser.objects.create_user(username=username, email=email, password=password, role=role, organization=organization, tenant=tenant)

        # Create a corresponding PostgreSQL role for the userx``
        with connection.cursor() as cursor:
            cursor.execute(f"CREATE ROLE {username} WITH LOGIN PASSWORD %s IN ROLE crm_tenant_{role};", [password])
            cursor.execute(f"GRANT crm_tenant_{role} TO {username};")

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
        if user:
            # Check user's role and tenant
            role = user.role
            tenant_id = user.tenant.id  # Get the tenant ID associated with the user
            user_id = user.id  # Get the user ID of the logged-in user

            # Construct the response based on the user's role
            if role == CustomUser.ADMIN:
                # Show admin views
                return Response({'msg': 'Login successful as admin', 'tenant_id': tenant_id, 'user_id': user_id,'role':user.role}, status=status.HTTP_200_OK)
            elif role == CustomUser.MANAGER:
                # Show manager views
                return Response({'msg': 'Login successful as manager', 'tenant_id': tenant_id, 'user_id': user_id,'role':user.role}, status=status.HTTP_200_OK)
            else:
                # Show employee views
                return Response({'msg': 'Login successful as employee', 'tenant_id': tenant_id, 'user_id': user_id,'role':user.role}, status=status.HTTP_200_OK)
        else:
            return Response({'msg': 'Invalid credentials'}, status=status.HTTP_401_UNAUTHORIZED)


class LogoutView(APIView):
    def post(self, request):
        # Log out the user
        logout(request)
        
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