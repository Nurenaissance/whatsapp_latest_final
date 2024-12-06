from celery import shared_task
from django.utils import timezone
from .models import Contact
import logging

logger = logging.getLogger(__name__)

@shared_task(bind=True, max_retries=3)
def update_contact_last_seen(self, phone, update_type, time, tenant):
    try:
        print("tasks update_contact_last_seen")
        if not all([phone, update_type, tenant]):
            raise ValueError("Missing required parameters")

        now = time or timezone.now()
        contact = Contact.objects.filter(phone=phone, tenant_id=tenant).first()
        if not contact:
            return False

        if update_type == "seen":
            contact.last_seen = now
        elif update_type == "delivered":
            contact.last_delivered = now
        elif update_type == "replied":
            contact.last_seen = now
            contact.last_replied = now
        else:
            raise ValueError("Invalid update type")

        contact.save()
        return True
    except Exception as exc:
        if isinstance(exc, (ValueError, Contact.DoesNotExist)):
            return False
        raise self.retry(exc=exc, countdown=2 ** self.request.retries)
