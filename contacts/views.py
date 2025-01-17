
from .models import Contact
from .serializers import ContactSerializer
from django.http import JsonResponse
from datetime import datetime
from rest_framework.exceptions import APIException
from rest_framework.response import Response
from rest_framework import status, views
from rest_framework.generics import ListCreateAPIView, RetrieveUpdateDestroyAPIView, CreateAPIView
from django.views.decorators.csrf import csrf_exempt
from helpers.tables import get_db_connection
from whatsapp_chat.models import WhatsappTenantData
from .tasks import update_contact_last_seen

class ContactListCreateAPIView(ListCreateAPIView):
    queryset = Contact.objects.all()
    serializer_class = ContactSerializer
    # permission_classes = (IsAdminUser,)  # Optionally, add permission classes

class ContactDetailAPIView(RetrieveUpdateDestroyAPIView):
    queryset = Contact.objects.all()
    serializer_class = ContactSerializer
    # permission_classes = (IsAdminUser,)  # Optionally, add permission classes

class ContactByAccountAPIView(ListCreateAPIView):
    serializer_class = ContactSerializer

    def get_queryset(self):
        account_id = self.kwargs.get('account_id')  # Get account ID from URL parameters
        return Contact.objects.filter(account_id=account_id)  # Filter by 
    
class ContactByPhoneAPIView(ListCreateAPIView):
    serializer_class = ContactSerializer

    def get_queryset(self):
        phone = self.kwargs.get('phone')
        print("phone : " ,phone)
        
        try:
            phone_str = str(phone)
            queryset = Contact.objects.filter(phone=phone_str)
            return queryset
        except Exception as e:
            print(f"An error occurred: {e}")
            raise APIException(f"An error occurred while fetching contacts: {e}")

class ContactByTenantAPIView(CreateAPIView):
    serializer_class = ContactSerializer

    def get_queryset(self):
        tenant_id = self.request.headers.get('X-Tenant-Id')
        return Contact.objects.filter(tenant_id=tenant_id)
    
    def create(self, request, *args, **kwargs):
        try:
            bpid = request.headers.get('bpid')
            whatsapp_tenant_data = get_object_or_404(WhatsappTenantData, business_phone_number_id=bpid)
            tenant_id = whatsapp_tenant_data.tenant_id

            contact_data = request.data
            name = contact_data.get('name')
            phone = contact_data.get('phone')

            contact_exists = Contact.objects.filter(tenant_id=tenant_id, phone=phone).exists()

            if contact_exists:
                contact = Contact.objects.get(tenant_id=tenant_id, phone=phone)
                if name:
                    contact.name = name
                    contact.save()
                return Response(
                    {"detail": "Contact already exists under this tenant."},
                    status=status.HTTP_200_OK
                )

            serializer = self.get_serializer(data=contact_data)
            serializer.is_valid(raise_exception=True)
            serializer.save(tenant_id=tenant_id)  # Save with tenant_id from headers
            return Response(serializer.data, status=status.HTTP_201_CREATED)

        except WhatsappTenantData.DoesNotExist:
            return Response(
                {"detail": "Tenant-ID header is required."},
                status=status.HTTP_400_BAD_REQUEST
            )
        except Exception as e:
            return Response(
                {"detail": str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
        
class UpdateContactAPIView(views.APIView):
    def patch(self, request, *args, **kwargs):
        try:
            data = request.data
            phone = data.get('phone')
            tenant_id = request.headers.get('X-Tenant-Id')

            errors = []
            contact = Contact.objects.filter(phone=phone, tenant_id=tenant_id).first()
            if not contact:
                raise Contact.DoesNotExist

            # Update all fields including 'template_key'
            for field, value in data.items():
                if hasattr(contact, field):
                    setattr(contact, field, value)

            contact.save()
            print(f"Contact {phone} updated successfully")
        except Contact.DoesNotExist:
            print("Error in fetching contact: ")
            errors.append(f"Contact with phone {phone} does not exist.")
        except Exception as e:
            print("Error: ", str(e))
            errors.append(str(e))

        if errors:
            return Response({"errors": errors}, status=status.HTTP_400_BAD_REQUEST)

        return Response({"message": "Contact updated successfully"}, status=status.HTTP_200_OK)
    
from django.shortcuts import get_object_or_404
from communication.models import Conversation
from topicmodelling.models import TopicModelling

def delete_contact_by_phone(request, phone_number):
    try:
        # Get the contact based on phone number
        contact = get_object_or_404(Contact, phone=phone_number)

        # Find all conversations related to this contact
        conversations = Conversation.objects.filter(contact_id=contact)

        # Loop through conversations and delete related TopicModelling entries
        for conversation in conversations:
            # Delete the related TopicModelling
            TopicModelling.objects.filter(conversation=conversation).delete()

            # Delete the conversation
            conversation.delete()

        # Finally, delete the contact
        contact.delete()

        return JsonResponse({"message": f"Contact with phone number {phone_number} and related data deleted successfully."}, status=200)

    except Contact.DoesNotExist:
        return JsonResponse({"message": f"Contact with phone number {phone_number} does not exist."}, status=404)

    except Exception as e:
        return JsonResponse({"message": str(e)}, status=500)

@csrf_exempt
def get_contacts_sql(req):
    if req.method == "GET":

        query = "SELECT * FROM public.contacts_contact"
        connection = get_db_connection()
        cursor = connection.cursor()
        cursor.execute(query)
        results = cursor.fetchall()

        columns = [col[0] for col in cursor.description]  # Get column names
        results = [dict(zip(columns, row)) for row in results]

        print(results)

        return JsonResponse(results , safe=False)


import logging
from .models import Contact

logger = logging.getLogger(__name__)


# views.py
import logging, json
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.utils.timezone import make_aware
from django.views.decorators.http import require_http_methods

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
        aware_time = make_aware(parsed_datetime)
        postgres_format = aware_time.strftime("%Y-%m-%d %H:%M:%S.%f")
        return postgres_format
    except ValueError as e:
        print(f"Error converting datetime: {e}")
        return None
    

@csrf_exempt
@require_http_methods(["PATCH"])
def updateLastSeen(request, phone, type):
    """
    Queue a last seen update for asynchronous processing
    
    :param request: HTTP request
    :param phone: Phone number of the contact
    :param type: Type of update (seen/delivered/replied)
    :return: JSON response
    """
    try:
        body = json.loads(request.body)
        raw_time = body.get("time")
        formatted_timestamp = convert_time(raw_time)
        
        bpid = request.headers.get('bpid')
        whatsapp_tenant_data = WhatsappTenantData.objects.filter(business_phone_number_id = bpid).first()
        tenant_id = whatsapp_tenant_data.tenant_id
        print("twenant id: " ,tenant_id)
        print("Data Received: ", raw_time, formatted_timestamp, tenant_id, phone, type)
        valid_types = ["seen", "delivered", "replied"]
        if type not in valid_types:
            return JsonResponse({
                "error": f"Invalid update type: {type}. Must be one of: " + ", ".join(valid_types)
            }, status=400)
        
        # Enhanced logging
        print("Attempting Queue")
        print(f"Attempting to queue task - Phone: {phone}, Type: {type}, Time: {formatted_timestamp}, Tenant: {tenant_id}")
        
        # Enqueue the task with additional error handling
        task = update_contact_last_seen.delay(phone, type, formatted_timestamp, tenant_id)
        print("task Queued")
        logger.info(f"Task queued successfully - Task ID: {task.id}")
        
        return JsonResponse({
            "success": True, 
            "message": "Update queued for processing",
            "task_id": task.id
        }, status=202)
    
    
    except json.JSONDecodeError:
        logger.error("Invalid JSON in request body")
        return JsonResponse({"error": "Invalid JSON in request body"}, status=400)
    
    except Exception as e:
        logger.error(f"Unexpected error in updateLastSeen: {e}")
        
        return JsonResponse({
            "error": "Internal server error", 
            "details": str(e)
        }, status=500)
    
    
# Optional: Task status checking view
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

