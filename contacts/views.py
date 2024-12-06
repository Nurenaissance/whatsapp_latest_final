
from .models import Contact
from .serializers import ContactSerializer
from django.http import JsonResponse
import datetime
from rest_framework.exceptions import APIException
from rest_framework.response import Response
from rest_framework import status, views
from rest_framework.generics import ListCreateAPIView, RetrieveUpdateDestroyAPIView, CreateAPIView
from django.views.decorators.csrf import csrf_exempt
from helpers.tables import get_db_connection

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
            print("phone : " ,phone_str)
            queryset = Contact.objects.filter(phone=phone_str)
            print("queryset: " ,queryset)
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
        tenant_id = request.headers.get('X-Tenant-Id')  # Get tenant_id from headers

        if not tenant_id:
            return Response(
                {"detail": "Tenant-ID header is required."},
                status=status.HTTP_400_BAD_REQUEST
            )

        contact_data = request.data

        name = contact_data.get('name')
        phone = contact_data.get('phone')

        try:
            # Check if a contact with the same phone and tenant_id already exists
            contact_exists = Contact.objects.filter(
                tenant_id=tenant_id,
                phone=phone
            ).exists()

            if contact_exists:
                return Response(
                    {"detail": "Contact already exists under this tenant."},
                    status=status.HTTP_200_OK
                )

            # If the contact doesn't exist, create a new one
            serializer = self.get_serializer(data=contact_data)
            serializer.is_valid(raise_exception=True)
            serializer.save(tenant_id=tenant_id)  # Save with tenant_id from headers
            return Response(serializer.data, status=status.HTTP_201_CREATED)

        except Exception as e:
            print(f"An error occurred: {e}")
            raise APIException(f"An error occurred while creating the contact: {e}")
        
class UpdateContactAPIView(views.APIView):
    def patch(self, request, *args, **kwargs):
        data = request.data
        contact_id = data.get('contact_id', [])
        bgID = data.get('bgid')
        bg_name = data.get('name')

        errors = []
        for phone in contact_id:
            try:
                contact = Contact.objects.get(id=phone)
                contact.bg_id = bgID
                print(bg_name)
                contact.bg_name = bg_name
                contact.save()
            except Contact.DoesNotExist:
                errors.append(f"Contact with id {phone} does not exist.")
            except Exception as e:
                errors.append(str(e))

        if errors:
            return Response({"errors": errors}, status=status.HTTP_400_BAD_REQUEST)

        return Response({"message": "Contacts updated successfully"}, status=status.HTTP_200_OK)

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

from django.utils import timezone

import logging
from celery import shared_task
from django.utils import timezone
from .models import Contact

logger = logging.getLogger(__name__)

@shared_task(bind=True, max_retries=3)
def update_contact_last_seen(self, phone, update_type, time):
    """
    Asynchronous task to update contact's last seen status
    
    :param self: Celery task instance
    :param phone: Phone number of the contact
    :param update_type: Type of update (seen/delivered/replied)
    """
    try:
        # Fetch contact by phone
        contact = Contact.objects.filter(phone=phone).first()
        
        if not contact:
            logger.warning(f"Contact not found for phone: {phone}")
            return False
        print("Contact Found: ", contact)
        now = time
        print("Updating Last Seen: " ,now)

        if update_type == "seen":
            contact.last_seen = now

        elif update_type == "delivered":
            contact.last_delivered = now

        elif update_type == "replied":
            contact.last_seen = now
            contact.last_replied = now

        else:
            logger.error(f"Invalid update type: {update_type}")
            return False
        
        # Save contact
        contact.save()
        
        logger.info(f"Successfully updated last {update_type} for contact {phone}")
        return True
    
    except Exception as exc:
        logger.error(f"Error updating contact last seen: {exc}")
        # Retry the task with exponential backoff
        raise self.retry(exc=exc, countdown=2 ** self.request.retries)

# views.py
import logging, json
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods

logger = logging.getLogger(__name__)

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
        time = body.get("time")
        valid_types = ["seen", "delivered", "replied"]
        if type not in valid_types:
            return JsonResponse({
                "error": "Invalid update type. Must be one of: " + ", ".join(valid_types)
            }, status=400)
        
        # Enqueue the task
        task = update_contact_last_seen.delay(phone, type, time)
        print("WABALABADUDUD")
        return JsonResponse({
            "success": True, 
            "message": "Update queued for processing",
            "task_id": task.id
        }, status=202)
    
    except Exception as e:
        logger.error(f"Unexpected error in updateLastSeen: {e}")
        return JsonResponse({"error": "Internal server error"}, status=500)

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

