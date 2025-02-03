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
            '/insert-data/',
            '/get-tenant/',
            '/whatsapp-media-uploads/',
            '/verifyTenant/',
            '/change-password/',
            '/password_reset/',
            '/reset/', 
            '/whatsapp_convo_get/',
            '/whatsapp_tenant',
            '/set-status/',
            '/update-last-seen/',
            '/add-key/',
            '/test-api/',
            '/contacts_by_tenant/',
            '/individual_message_statistics/',
            '/payments-webhook'
        ]
        # Check if the request path starts with any of the paths to skip
        if any(request.path.startswith(path) for path in paths_to_skip):
            print(f"Skipping tenant processing for path: {request.path}")
            return

        tenant_id = request.headers.get('X-Tenant-Id')
        
        print(f"Received Tenant ID: {tenant_id}")


        if not tenant_id:
            print("No Tenant ID found in headers", request.path)
            return HttpResponse('No Tenant ID provided', status=400)
        print("current tenant " , TenantMiddleware.current_tenant_id)
        
        # connection = connections['default']
        # print("username and pw 1: ", connection.settings_dict['USER'], connection.settings_dict['PASSWORD'])
        if TenantMiddleware.current_tenant_id == tenant_id:
            print(f"Tenant ID {tenant_id} already connected. Skipping reconnection.")
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
            
            # Debug: Print original connection settings before modification
            print("Original connection settings:")
            print(f"Original USER: {connection.settings_dict['USER']}")
            print(f"Original PASSWORD: {connection.settings_dict['PASSWORD']}")

            # Set new credentials
            connection.settings_dict['USER'] = tenant_username
            connection.settings_dict['PASSWORD'] = tenant_password
            
            print("New connection settings:")
            print(f"New USER: {connection.settings_dict['USER']}")
            print(f"New PASSWORD: {connection.settings_dict['PASSWORD']}")

            logger.debug(f"Attempting to set database user to: {tenant_username}")

            try:
                connection.close()
                print("Attempting to re-establish connection")
                connection.connect()
                print("Connection re-established successfully")
            except Exception as connect_error:
                print(f"Failed to re-establish connection: {connect_error}")
                logger.error(f"Connection re-establishment failed: {connect_error}")

        except DatabaseError as e:
            print(f"Database error occurred: {e}")
            logger.error(f"Database error: {e}")
        except Exception as e:
            print(f"Unexpected error in tenant middleware: {e}")
            logger.error(f"Unexpected error: {e}")
        finally:
            TenantMiddleware.current_tenant_id = tenant_id
            # Ensure you don't expose sensitive credentials in production logs
            print("Credentials handling completed")


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
