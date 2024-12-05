from celery import shared_task
from django.db import transaction
from .models import Conversation
import logging

logger = logging.getLogger(__name__)

@shared_task(bind=True, max_retries=3)
def process_conversations(self, payload):
    try:
        print("PRocessing conv")
        with transaction.atomic():
            contact_id = payload['contact_id']
            conversations = payload['conversations']
            tenant = payload['tenant']
            source = payload['source']
            bpid = payload['business_phone_number_id']

            # Bulk create conversations (in batches to avoid overwhelming DB)
            batch_size = 100  # Adjust the batch size if needed
            for i in range(0, len(conversations), batch_size):
                batch = conversations[i:i + batch_size]
                conversations_to_create = [
                    Conversation(
                        contact_id=contact_id, 
                        message_text=message.get('text', ''),
                        sender=message.get('sender', ''),
                        tenant_id=tenant,
                        source=source,
                        business_phone_number_id=bpid
                    ) for message in batch
                ]
                Conversation.objects.bulk_create(conversations_to_create)

    except Exception as exc:
        logger.error(f"Error processing conversations: {exc}")
        # Retry with exponential backoff
        self.retry(exc=exc, countdown=2 ** self.request.retries)
