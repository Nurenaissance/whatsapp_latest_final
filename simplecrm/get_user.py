from django.shortcuts import get_object_or_404
from .models import CustomUser
from django.views.decorators.csrf import csrf_exempt
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
# Import other necessary modules as needed...
import json
# Endpoint to retrieve user details by username
@csrf_exempt
@require_http_methods(["GET", "PUT"])
def get_user_by_username(request, username):
    user = get_object_or_404(CustomUser, username=username)

    if request.method == 'GET':
        user_data = {
            'id': user.id,
            'username': user.username,
            'email': user.email,
            'role': user.role,
            'name': user.name,
            'phone_number': user.phone_number,
            'address': user.address,
            'job_profile': user.job_profile,
        }
        return JsonResponse(user_data)
    elif request.method == 'PUT':
        try:
            data = json.loads(request.body)
            user.name = data.get('name', user.name)
            user.email = data.get('email', user.email)
            user.phone_number = data.get('phone_number', user.phone_number)
            user.address = data.get('address', user.address)
            user.job_profile = data.get('job_profile', user.job_profile)
            user.save()

            # Return updated user details
            updated_user_data = {
                'id': user.id,
                'username': user.username,
                'email': user.email,
                'role': user.role,
                'name': user.name,
                'phone_number': user.phone_number,
                'address': user.address,
                'job_profile': user.job_profile,
            }
            return JsonResponse(updated_user_data)
        except json.JSONDecodeError:
            return JsonResponse({'error': 'Invalid JSON'}, status=400)

# Endpoint to retrieve user details by user ID
@csrf_exempt
@require_http_methods(["GET", "PUT"])
def user_details_by_id(request, user_id):
    user = get_object_or_404(CustomUser, id=user_id)

    if request.method == 'GET':
        user_data = {
            'id': user.id,
            'username': user.username,
            'email': user.email,
            'role': user.role,
            'name': user.name,
            'phone_number': user.phone_number,
            'address': user.address,
            'job_profile': user.job_profile,
        }
        return JsonResponse(user_data)
    elif request.method == 'PUT':
        try:
            data = json.loads(request.body)
            user.name = data.get('name', user.name)
            user.email = data.get('email', user.email)
            user.phone_number = data.get('phone_number', user.phone_number)
            user.address = data.get('address', user.address)
            user.job_profile = data.get('job_profile', user.job_profile)
            user.save()

            # Return updated user details
            updated_user_data = {
                'id': user.id,
                'username': user.username,
                'email': user.email,
                'role': user.role,
                'name': user.name,
                'phone_number': user.phone_number,
                'address': user.address,
                'job_profile': user.job_profile,
            }
            return JsonResponse(updated_user_data)
        except json.JSONDecodeError:
            return JsonResponse({'error': 'Invalid JSON'}, status=400)
        
@csrf_exempt
@require_http_methods(["GET"])
def get_all_users(request):
    tenant_id = request.headers.get('X-Tenant-Id')
    if not tenant_id:
        return JsonResponse({'error': 'Tenant-ID header is required'}, status=400)

    users = CustomUser.objects.filter(tenant_id=tenant_id)
    users_data = []
    for user in users:
        user_data = {
            'id': user.id,
            'username': user.username,
            'email': user.email,
            'role': user.role,
            'name': user.name,
            'phone_number': user.phone_number,
            'address': user.address,
            'job_profile': user.job_profile,
        }
        users_data.append(user_data)
    return JsonResponse(users_data, safe=False)