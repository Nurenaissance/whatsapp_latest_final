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