from celery import shared_task
from django.db import transaction
from .models import Conversation
import logging
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.backends import default_backend
import os
import json


logger = logging.getLogger(__name__)

@shared_task(bind=True, max_retries=3)
def process_conversations(self, payload, key):
    try:
        print("tasks PRocessing conv")
        with transaction.atomic():
            contact_id = payload['contact_id']
            conversations = payload['conversations']
            tenant = payload['tenant']
            source = payload['source']
            bpid = payload['business_phone_number_id']
            
            if isinstance(key, memoryview):
                key = bytes(key)

            encryption_key = key    
            print("Type of key: ", type(encryption_key))
            # Bulk create conversations (in batches to avoid overwhelming DB)
            batch_size = 100  # Adjust the batch size if needed
            for i in range(0, len(conversations), batch_size):
                batch = conversations[i:i + batch_size]
                conversations_to_create = [
                    Conversation(
                        contact_id=contact_id, 
                        # message_text=message.get('text', ''),
                        encrypted_message_text = encrypt_data(data=message.get('text', ''), key=encryption_key),
                        sender=message.get('sender', ''),
                        tenant_id=tenant,
                        source=source,
                        business_phone_number_id=bpid,
                        date_time = payload['time']
                    ) for message in batch
                ]
                Conversation.objects.bulk_create(conversations_to_create)

    except Exception as exc:
        logger.error(f"Error processing conversations: {exc}")
        # Retry with exponential backoff
        self.retry(exc=exc, countdown=2 ** self.request.retries)

def encrypt_data(data, key):
    data_str = json.dumps(data)
    
    iv = os.urandom(16)  # AES block size is 16 bytes
    cipher = Cipher(algorithms.AES(key), modes.CBC(iv), backend=default_backend())
    encryptor = cipher.encryptor()


    pad_len = 16 - len(data_str) % 16
    data_str += chr(pad_len) * pad_len

    encrypted_data = encryptor.update(data_str.encode()) + encryptor.finalize()


    return iv + encrypted_data
