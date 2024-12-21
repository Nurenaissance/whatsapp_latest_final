from celery import shared_task
from django.db import transaction
from datetime import datetime
from django.db import connection
import requests

@shared_task(bind=True, max_retries=3, queue = 'message_status_queue')
def process_message_status(self, payload):
    try:
        print("task process message status")
        with transaction.atomic():
            messageID = payload['message_id']
            data = payload['data']
            tenant_id = payload['tenant_id']

            # Convert timestamp
            time = data.get('timestamp')

            try:
                time = datetime.strptime(time, "%Y-%m-%d %H:%M:%S.%f")
            except ValueError:
                time = datetime.strptime(time, "%Y-%m-%d %H:%M:%S")

            
            # Bulk upsert query
            with connection.cursor() as cursor:
                query = """
                    INSERT INTO whatsapp_message_id (
                        message_id, business_phone_number_id, sent, 
                        delivered, read, replied, failed, 
                        user_phone_number, broadcast_group, 
                        broadcast_group_name, template_name, 
                        tenant_id, last_seen
                    ) VALUES (
                        %s, %s, %s, %s, %s, %s, %s, %s, 
                        %s, %s, %s, %s, %s
                    ) ON CONFLICT (message_id) DO UPDATE SET
                        sent = EXCLUDED.sent,
                        delivered = EXCLUDED.delivered,
                        read = EXCLUDED.read,
                        failed = EXCLUDED.failed,
                        replied = EXCLUDED.replied,
                        last_seen = EXCLUDED.last_seen
                """
                cursor.execute(query, [
                    messageID, 
                    data.get('business_phone_number_id'),
                    data.get('is_sent', False),
                    data.get('is_delivered', False),
                    data.get('is_read', False),
                    data.get('is_replied', False),
                    data.get('is_failed', False),
                    data.get('user_phone'),
                    data.get('bg_id'),
                    data.get('bg_name'),
                    data.get('template_name'),
                    tenant_id,
                    time
                ])

                
    except Exception as exc:
        # Retry with exponential backoff
        self.retry(exc=exc, countdown=2 ** self.request.retries)
