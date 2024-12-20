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
            timestamp_seconds = int(int(time) / 1000)
            datetime_obj = datetime.fromtimestamp(timestamp_seconds)
            postgres_timestamp = datetime_obj.strftime('%Y-%m-%d %H:%M:%S')

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
                    postgres_timestamp
                ])
                print("MOVING TO PROCESS NEW SET STATUS")
                process_new_set_status(payload=payload)

                
    except Exception as exc:
        # Retry with exponential backoff
        self.retry(exc=exc, countdown=2 ** self.request.retries)

def process_new_set_status(payload):
    try: 
        with transaction.atomic():
            message_id = payload['message_id']
            data = payload['data']
            tenant_id = payload['tenant_id']

        template_name, bg_group = get_template_name(message_id)

        key = bg_group or template_name
        print("Key : ", key)

        if key is None:
            return
        
        update_fields = []
        flag_to_column = {
            'is_sent': 'sent',
            'is_delivered': 'delivered',
            'is_read': 'read',
            'is_replied': 'replied',
            'is_failed': 'failed'
        }

        for flag, column in flag_to_column.items():
            if data.get(flag) is True:
                print("Column found: ", column)
                update_fields.append(f"{column} = {column} + 1")

    
        with connection.cursor() as cursor:
            cursor.execute(f"SELECT 1 FROM new_set_status WHERE name = %s;", (key,))
            row_exists = cursor.fetchone()

            if row_exists:
                print("Row Exists: ", key)
                if update_fields:

                    update_query = f"UPDATE new_set_status SET {', '.join(update_fields)} WHERE name = %s;"
                    cursor.execute(update_query, (key,))
                    message = "Record updated successfully."
                else:
                    message = "No updates were made as no flags were set to True."
            else:
                print("Row does not exist: ", key)
                insert_query = """
                INSERT INTO new_set_status (name, tenant_id, sent, delivered, read, replied, failed)
                VALUES (%s, %s, 1, 0, 0, 0, 0);
                """
                cursor.execute(insert_query, (key, tenant_id))
                message = "New record created successfully."

        print("Message: " ,message)
    except Exception as exc: 
        print("An Exception Occured in process_new_set_status: ", exc)


def get_template_name(message_id):
    print("rcvd message id: ", message_id)
    sql_query = """
    SELECT template_name, broadcast_group_name
    FROM whatsapp_message_id
    WHERE message_id = %s;
    """
    
    cursor = connection.cursor()
    cursor.execute(sql_query, (message_id,))
    
    result = cursor.fetchone()
    print("Result: ", result)
    if result:
        template_name, broadcast_group_name = result
        return template_name, broadcast_group_name
    else:
        return None, None
