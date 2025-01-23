from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
from django.views import View
from django.shortcuts import get_object_or_404
from django.db import IntegrityError, transaction
import json
from .models import MessageStatistics, IndividualMessageStatistics

class MessageStatisticsView(View):
    @method_decorator(csrf_exempt)
    def dispatch(self, *args, **kwargs):
        return super().dispatch(*args, **kwargs)

    def get(self, request, *args, **kwargs):
        """
        Fetch data based on query parameters or return all entries.
        """
        name = request.GET.get("name")
        tenant_id = request.headers.get("X-Tenant-Id")
        
        
        if name and tenant_id:
            entry = get_object_or_404(MessageStatistics, name=name, tenant_id=tenant_id)
            return JsonResponse({"data": self.serialize_entry(entry)}, status=200)
        
        entries = MessageStatistics.objects.all()
        data = [self.serialize_entry(entry) for entry in entries]
        return JsonResponse({"data": data}, status=200, safe=False)

    def post(self, request, *args, **kwargs):
        return self.create_or_update(request)

    def patch(self, request, *args, **kwargs):
        return self.create_or_update(request)

    def create_or_update(self, request):
        """
        Create a new entry or update an existing one based on `name` and `tenant_id`.
        """
        try:
            data = json.loads(request.body)
            name = data.get('name')
            tenant_id = request.headers.get('X-Tenant-Id')

            if not name or not tenant_id:
                return JsonResponse({"error": "Both 'name' and 'tenant_id' are required."}, status=400)

            with transaction.atomic():
                entry, created = MessageStatistics.objects.get_or_create(
                    name=name, tenant_id=tenant_id,
                    defaults={key: value for key, value in data.items() if key not in ['name', 'tenant_id']}
                )

                if not created:
                    for key, value in data.items():
                        if key not in ['name', 'tenant_id'] and hasattr(entry, key):

                            if key == 'sent':
                                setattr(entry, key, getattr(entry, key, 0) + value)
                            else:
                                setattr(entry, key, value)                    
                    entry.save()
                message = "Entry created successfully" if created else "Entry updated successfully"
                return JsonResponse({"message": message, "data": self.serialize_entry(entry)})

        except IntegrityError:
            return JsonResponse({"error": "Integrity error. Please check the provided data."}, status=400)
        except Exception as e:
            return JsonResponse({"error": f"An error occurred: {str(e)}"}, status=500)

    def serialize_entry(self, entry):
        """
        Serialize a MessageStatistics instance into a dictionary.
        """
        return {
            "id": entry.id,
            "name": entry.name,
            "sent": entry.sent,
            "delivered": entry.delivered,
            "read": entry.read,
            "replied": entry.replied,
            "failed": entry.failed,
            "tenant_id": entry.tenant_id,
            "type": entry.type
        }


class IndividualMessageStatisticsView(View):
    @method_decorator(csrf_exempt)
    def dispatch(self, *args, **kwargs):
        return super().dispatch(*args, **kwargs)

    def get(self, request, *args, **kwargs):
        """
        Fetch data based on query parameters or return all entries.
        """
        message_id = request.GET.get("message_id")
        tenant_id = request.headers.get("X-Tenant-Id")

        if message_id and tenant_id:
            entry = get_object_or_404(IndividualMessageStatistics, message_id=message_id, tenant_id=tenant_id)
            return JsonResponse({"data": self.serialize_entry(entry)}, status=200)
        
        entries = IndividualMessageStatistics.objects.all()
        data = [self.serialize_entry(entry) for entry in entries]
        return JsonResponse({"data": data}, status=200, safe=False)

    def post(self, request, *args, **kwargs):
        return self.create_or_update(request)

    def patch(self, request, *args, **kwargs):
        return self.create_or_update(request)

    def create_or_update(self, request):
        """
        Create a new entry or update an existing one based on `message_id` and `tenant_id`.
        """
        try:
            data = json.loads(request.body)
            message_id = data.get('message_id')
            bpid = request.headers.get('bpid')

            if not message_id or not bpid:
                return JsonResponse({"error": "Both 'message_id' and 'bpid' are required."}, status=400)

            with transaction.atomic():
                entry, created = IndividualMessageStatistics.objects.get_or_create(
                    message_id=message_id, bpid=bpid,
                    defaults={key: value for key, value in data.items() if key not in ['message_id', 'bpid']}
                )

                if not created:
                    for key, value in data.items():
                        if key not in ['message_id', 'bpid'] and hasattr(entry, key):
                            if key == 'sent':
                                setattr(entry, key, getattr(entry, key, 0) + value)
                            else:
                                setattr(entry, key, value)                    
                    entry.save()

                message = "Entry created successfully" if created else "Entry updated successfully"
                return JsonResponse({"message": message, "data": self.serialize_entry(entry)})

        except IntegrityError:
            return JsonResponse({"error": "Integrity error. Please check the provided data."}, status=400)
        except Exception as e:
            return JsonResponse({"error": f"An error occurred: {str(e)}"}, status=500)

    def serialize_entry(self, entry):
        """
        Serialize an IndividualMessageStatistics instance into a dictionary.
        """
        return {
            "id": entry.id,
            "message_id": entry.message_id,
            "status": entry.status,
            "type": entry.type,
            "userPhone": entry.userPhone,
            "tenant_id": entry.tenant_id,
            "bpid": entry.bpid,
            "timestamp": entry.timestamp,
            "template_name": entry.template_name
        }
    

from django.http import JsonResponse, HttpResponseBadRequest, HttpResponseServerError
from django.db import transaction, IntegrityError
from datetime import timedelta
from contacts.models import Contact  # Replace with your actual models


# @csrf_exempt
# def refresh_status(request):
#     try:
#         tenant_id = request.headers.get("X-Tenant-Id")
#         if not tenant_id:
#             return HttpResponseBadRequest("Missing Tenant ID in headers")

#         with transaction.atomic():
#             # Fetch all IndividualMessageStatistics for the tenant
#             statuses = IndividualMessageStatistics.objects.filter(tenant_id=tenant_id)

#             # Group statuses by broadcast_group or template_name
#             grouped_statuses = {}
#             for status in statuses:
#                 bg_group = status.broadcast_group
#                 template_name = status.template_name
#                 key = bg_group if bg_group else template_name

#                 if key not in grouped_statuses:
#                     grouped_statuses[key] = {
#                         "name": status.broadcast_group_name or None,
#                         "sent": 0,
#                         "delivered": 0,
#                         "read": 0,
#                         "replied": 0,
#                         "failed": 0,
#                         "template_name": template_name,
#                     }

#                 if status.sent:
#                     grouped_statuses[key]["sent"] += 1
#                 if status.delivered:
#                     grouped_statuses[key]["delivered"] += 1
#                 if status.read:
#                     grouped_statuses[key]["read"] += 1
#                 if status.replied:
#                     grouped_statuses[key]["replied"] += 1
#                 if status.failed:
#                     grouped_statuses[key]["failed"] += 1

#             # Fetch all contacts for the tenant
#             contacts = Contact.objects.filter(tenant_id=tenant_id).order_by("id")

#             for contact in contacts:
#                 key = contact.template_key or f"Untracked_{tenant_id}"
#                 delivered = contact.last_delivered
#                 replied = contact.last_replied

#                 if delivered is None or replied is None:
#                     continue

#                 if key not in grouped_statuses:
#                     grouped_statuses[key] = {
#                         "name": "Group B",
#                         "sent": 0,
#                         "delivered": 0,
#                         "read": 0,
#                         "replied": 0,
#                         "failed": 0,
#                         "template_name": "Untracked",
#                     }

#                 time_diff = delivered - replied
#                 if time_diff < timedelta(minutes=1):
#                     grouped_statuses[key]["replied"] += 1

#             # Update or create MessageStatistics records
#             for key, status_data in grouped_statuses.items():
#                 existing_record = IndividualMessageStatistics.objects.filter(
#                     tenant_id=tenant_id, record_key=key
#                 ).first()

#                 if existing_record:
#                     existing_record.name = status_data["name"]
#                     existing_record.sent = status_data["sent"]
#                     existing_record.delivered = status_data["delivered"]
#                     existing_record.read = status_data["read"]
#                     existing_record.replied = status_data["replied"]
#                     existing_record.failed = status_data["failed"]
#                     existing_record.template_name = status_data["template_name"]
#                     existing_record.save()
#                 else:
#                     IndividualMessageStatistics.objects.create(
#                         tenant_id=tenant_id,
#                         record_key=key,
#                         name=status_data["name"],
#                         sent=status_data["sent"],
#                         delivered=status_data["delivered"],
#                         read=status_data["read"],
#                         replied=status_data["replied"],
#                         failed=status_data["failed"],
#                         template_name=status_data["template_name"],
#                     )

#             return JsonResponse({"message": "Message statistics updated successfully"})

#     except IntegrityError as e:
#         return HttpResponseBadRequest(f"Database integrity error: {str(e)}")
#     except Exception as e:
#         return HttpResponseServerError(f"An unexpected error occurred: {e}")
    
@csrf_exempt
def refresh_status(request):
    try:
        tenant_id = request.headers.get("X-Tenant-Id")
        if not tenant_id:
            return HttpResponseBadRequest("Missing Tenant ID in headers")
        
        messages = IndividualMessageStatistics.objects.filter(tenant_id=tenant_id)

        template_data = {}
        campaign_data = {}
        group_data = {}

        contactMap = {}

        for message in messages:
            type_ = message.type 
            type_identifier = message.type_identifier 
            status = message.status 
            phone = message.userPhone
            

            if phone not in contactMap:
                contact = Contact.objects.filter(phone = phone, tenant_id = tenant_id).first()
                if contact:
                    if contact.last_replied > contact.last_delivered:
                        contactMap[phone] = {"replied": True}
                    else:
                        contactMap[phone] = {"replied": False}
                else:
                    contactMap[phone] = {"replied": False}

            if status == "replied":
                contactMap[phone]["replied"] = True
            
            
            if type_ == 'template':
                if type_identifier not in template_data:
                    template_data[type_identifier] = {'sent': 0, 'delivered': 0, 'read': 0, 'failed': 0, 'replied': 0}
                template_data[type_identifier][status] += 1
                
                if contactMap[phone]["replied"]:
                    template_data[type_identifier]["replied"] += 1

            elif type_ == 'campaign':
                if type_identifier not in campaign_data:
                    campaign_data[type_identifier] = {'sent': 0, 'delivered': 0, 'read': 0, 'failed': 0, 'replied': 0}
                campaign_data[type_identifier][status] += 1
                if contactMap[phone]["replied"]:
                    template_data[type_identifier]["replied"] += 1


            elif type_ == 'group':
                if type_identifier not in group_data:
                    group_data[type_identifier] = {'sent': 0, 'delivered': 0, 'read': 0, 'failed': 0, 'replied': 0}
                group_data[type_identifier][status] += 1
                if contactMap[phone]["replied"]:
                    template_data[type_identifier]["replied"] += 1


        for name, counts in template_data.items():
            MessageStatistics.objects.update_or_create(
                name=name, type='template', tenant_id = tenant_id,
                defaults={
                    'sent': counts['sent'],
                    'delivered': counts['delivered'],
                    'read': counts['read'],
                    'replied': counts['replied'],
                    'failed': counts['failed']
                }
            )

        for name, counts in campaign_data.items():
            MessageStatistics.objects.update_or_create(
                name=name, type='campaign', tenant_id = tenant_id,
                defaults={
                    'sent': counts['sent'],
                    'delivered': counts['delivered'],
                    'read': counts['read'],
                    'replied': counts['replied'],
                    'failed': counts['failed']
                }
            )

        for name, counts in group_data.items():
            MessageStatistics.objects.update_or_create(
                name=name, type='group', tenant_id = tenant_id,
                defaults={
                    'sent': counts['sent'],
                    'delivered': counts['delivered'],
                    'read': counts['read'],
                    'replied': counts['replied'],
                    'failed': counts['failed']
                }
            )

        return JsonResponse({"Success": True, "message": "Main table updated successfully!"})
    except Exception as e:
        print("Error occured in refresh_status: ", e)
        return JsonResponse({"Success": False, "message": e})
