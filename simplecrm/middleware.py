from django.db import connections, DatabaseError
from django.utils.deprecation import MiddlewareMixin
from django.http import HttpResponse
from .models import Tenant  # Ensure this is the correct path to your Tenant model
import logging
from datetime import datetime
from helpers.tables import get_db_connection


logger = logging.getLogger(__name__)

class TenantMiddleware(MiddlewareMixin):
    current_tenant_id = None

    def process_request(self, request):
        logger.debug("Processing request in TenantMiddleware")
        paths_to_skip = [
            '/login/',
            '/register/',
            '/createTenant/',
            '/track_open/',
            '/track_open_count/',
            '/track_click/',
            '/create_table/',
            '/insert_data/',
            '/whatsapp_tenant/',
            '/get-tenant/',
            '/whatsapp-media-uploads/',
            '/verifyTenant/',
            '/change-password/',
            '/password_reset/',
            '/reset/'
        ]
        
        # Check if the request path starts with any of the paths to skip
        if any(request.path.startswith(path) for path in paths_to_skip):
            print(f"Skipping tenant processing for path: {request.path}")
            return

        tenant_id = request.headers.get('X-Tenant-Id')
        
        print(f"Received Tenant ID: {tenant_id}")

        if not tenant_id:
            logger.error("No Tenant ID found in headers")
            return HttpResponse('No Tenant ID provided', status=400)
        print("current tenant " , TenantMiddleware.current_tenant_id)
        if TenantMiddleware.current_tenant_id == tenant_id:
            logger.debug(f"Tenant ID {tenant_id} already connected. Skipping reconnection.")
            return

        # Retrieve tenant's username and password from database
        try:
            tenant = Tenant.objects.get(id=tenant_id)  # Use the 'id' field for tenant_id
            print("tenant: " ,tenant)
            tenant_username = tenant.db_user
            print("username: " ,tenant_username)
            tenant_password = tenant.db_user_password
            print("pw: " ,tenant_password)
            logger.debug(f"Tenant found: {tenant}")
        except Tenant.DoesNotExist:
            # Handle case where tenant does not exist
            logger.error(f"Tenant does not exist for Tenant ID: {tenant_id}")
            print("tenant doesnt exist: ", tenant_id)
            return HttpResponse('Tenant does not exist', status=404)
        
        try:
            # Set the database connection settings for the tenant
            connection = connections['default']
            connection.settings_dict['USER'] = tenant_username
            connection.settings_dict['PASSWORD'] = tenant_password
            logger.debug(f"Set database user to: {tenant_username}")

            # Ensure the connection is re-established
            connection.close()
            connection.connect()
            logger.debug("Database connection re-established")

        except DatabaseError as e:
            logger.error(f"Database error occurred: {e}")
            # Handle database-related errors here
        except Exception as e:
            logger.error(f"An unexpected error occurred at tenant iddleware: {e}")
            # Handle any other unexpected errors here

        # Update the current tenant ID
        TenantMiddleware.current_tenant_id = tenant_id


class LogRequestTimeMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    # def log(platform, lead_stage, lead_id, timestamp, user_id):
    #     sql_query = f"""
    #     INSERT INTO communication_behavioralmetrics
    #     VALUES ({lead_id}, {interaction_count}, {avg_response_time}, {timestamp}, {score}, {user_id}, {platform}, {stage})
    #     """

    #     conn = get_db_connection()
    #     cursor = conn.cursor()
    #     cursor.execute(f"SELECT MAX(interaction_count) FROM communication_behavioralmetrics WHERE id = {lead_id}")
    #     mic=cursor.fetchone()[0]
    #     interaction_count = mic+1;

    #     cursor.execute()

    def __call__(self, request):
        timestamp = datetime.now().isoformat()
        endpoint = request.path
        log_message= f"Request received at: {timestamp} for endpoint: {endpoint}"
        print(log_message)
        logger.info(log_message)

        response = self.get_response(request)
        return response
