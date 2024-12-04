from simplecrm.celery import shared_task
from django.db import transaction
from models import Conversation

@shared_task(bind=True, max_retries=3)
def process_conversations(self, payload):
    try:
        with transaction.atomic():
            contact_id = payload['contact_id']
            conversations = payload['conversations']
            tenant = payload['tenant']
            source = payload['source']
            bpid = payload['business_phone_number_id']

            # Bulk create conversations
            conversations_to_create = [
                Conversation(
                    contact_id=contact_id, 
                    message_text=message.get('text', ''),
                    sender=message.get('sender', ''),
                    tenant_id=tenant,
                    source=source,
                    business_phone_number_id=bpid
                ) for message in conversations
            ]
            
            Conversation.objects.bulk_create(conversations_to_create)

    except Exception as exc:
        # Retry with exponential backoff
        self.retry(exc=exc, countdown=2 ** self.request.retries)