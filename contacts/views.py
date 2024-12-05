
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

@csrf_exempt
def updateLastSeen(request, phone, type):
    try:
        if request.method == "PATCH":
            # Fetch contact by phone from URL parameter
            contact = Contact.objects.filter(phone=phone).first()
            if not contact:
                return JsonResponse({"error": "Contact not found"}, status=404)

            # Update last_seen
            if type == "seen":
                contact.last_seen = timezone.now()
            elif type == "delivered":
                contact.last_delivered = timezone.now()
            elif type == "replied":
                contact.last_replied = timezone.now()
                contact.last_seen = timezone.now()
            
            contact.save()

            return JsonResponse({"success": True, "message": "Last seen updated successfully"})

        else:
            return JsonResponse({"error": "Invalid request method"}, status=405)

    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)