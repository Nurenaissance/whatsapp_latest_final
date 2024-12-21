from django.shortcuts import get_object_or_404
from rest_framework import status, generics
from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework.views import APIView
from datetime import datetime
from .models import Conversation,Group
from tenant.models import Tenant
from django.contrib.contenttypes.models import ContentType
from .serializers import GroupSerializer
from rest_framework.generics import ListCreateAPIView, RetrieveUpdateDestroyAPIView
from rest_framework import viewsets
from django.http import JsonResponse
from django.db.models import Count
import random
from django.views.decorators.csrf import csrf_exempt
import json, os
from django.db import transaction
from django.views.decorators.http import require_http_methods
from django.utils.timezone import make_aware
import re
import logging
logger = logging.getLogger('simplecrm')

import json
import logging
from typing import List, Dict

from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from .tasks import process_conversations
from redis import Redis, ConnectionPool
from azure.core.exceptions import AzureError

# Redis Connection Pool Configuration
REDIS_CONFIG = {
    'host': 'whatsappnuren.redis.cache.windows.net',
    'port': 6379,
    'password': 'O6qxsVvcWHfbwdgBxb1yEDfLeBv5VBmaUAzCaJvnELM=',
    # 'ssl': True,
    'max_connections': 50  # Adjust based on your infrastructure
}

redis_pool = ConnectionPool(**REDIS_CONFIG)
redis_client = Redis(connection_pool=redis_pool)
logger = logging.getLogger(__name__)


def convert_time(datetime_str):
    """
    Converts a date-time string from 'DD/MM/YYYY, HH:MM:SS.SSS'
    to PostgreSQL-compatible 'YYYY-MM-DD HH:MM:SS.SSS' format.
    
    Args:
        datetime_str (str): The date-time string to be converted.
    
    Returns:
        str: Converted date-time string in PostgreSQL format.
    """
    try:
        # Parse the input date-time string
        parsed_datetime = datetime.strptime(datetime_str, "%d/%m/%Y, %H:%M:%S.%f")
        # Convert it to the PostgreSQL-compatible format
        postgres_format = parsed_datetime.strftime("%Y-%m-%d %H:%M:%S.%f")
        return postgres_format
    except ValueError as e:
        print(f"Error converting datetime: {e}")
        return None
    

def create_conversation_objects(payload: Dict) -> List[Conversation]:
    return [
        Conversation(
            contact_id=payload['contact_id'],
            message_text=message.get('text', ''),
            sender=message.get('sender', ''),
            tenant_id=payload['tenant'],
            source=payload['source'],
            business_phone_number_id=payload['business_phone_number_id'],
            date_time = payload['time']
        ) for message in payload['conversations']
    ]

def bulk_create_with_batching(objects: List, batch_size: int = 500):
    """Bulk create with batch processing to prevent memory overload"""
    for i in range(0, len(objects), batch_size):
        batch = objects[i:i+batch_size]
        Conversation.objects.bulk_create(batch, ignore_conflicts=True)


# Encrypt the data using AES symmetric encryption

@csrf_exempt
def save_conversations(request, contact_id):
    try:
        # Enhanced rate limiting with sliding window
        # print("checking rate limit")
        if not check_rate_limit(request):
            return JsonResponse({'error': 'Rate limit exceeded'}, status=429)
        # print("Starting")
        payload = extract_payload(request)
        if 'time' in payload:
            raw_time = payload['time']
            
            # Remove commas
            
            try:
                postgres_timestamp = convert_time(raw_time)
                
                payload['time'] = postgres_timestamp
                
            except ValueError as e:
                print(f"Error processing time: {e}")

        tenant_id = payload['tenant']
        tenant = Tenant.objects.get(id = tenant_id)
        key = tenant.key
        
        if isinstance(key, memoryview):
            key = bytes(key)

        # print("payload: ", payload)

        # Asynchronous processing with error tracking
        process_conversations.delay(payload, key)
        print("process convo: ")
        
        return JsonResponse({"message": "Conversations queued for processing"}, status=202)
    
    except Exception as e:
        return handle_error(e)

def check_rate_limit(request, max_requests: int = 100, window: int = 60) -> bool:
    """Implement sliding window rate limiting"""
    client_ip = get_client_ip(request)
    rate_limit_key = f'conversations_ratelimit:{client_ip}'
    
    with redis_client.pipeline() as pipe:
        pipe.incr(rate_limit_key)
        pipe.expire(rate_limit_key, window)
        current_count, _ = pipe.execute()
    
    return current_count <= max_requests

def extract_payload(request) -> Dict:
    """Validate and extract request payload"""
    if request.method != 'POST':
        raise ValueError("Invalid request method")
    
    body = json.loads(request.body)
    return {
        'contact_id': request.resolver_match.kwargs['contact_id'],
        'conversations': body.get('conversations', []),
        'tenant': body.get('tenant'),
        'source': request.GET.get('source', ''),
        'business_phone_number_id': body.get('business_phone_number_id'),
        'time': body.get('time')
    }

def handle_error(error):
    """Centralized error handling"""
    if isinstance(error, json.JSONDecodeError):
        logger.error(f"JSON decode error: {error}")
        return JsonResponse({'error': 'Invalid JSON format'}, status=400)
    elif isinstance(error, AzureError):
        logger.error(f"Azure Redis error: {error}")
        return JsonResponse({'error': 'Cache service unavailable'}, status=503)
    else:
        logger.error(f"Unexpected error in handle error: {error}")
        return JsonResponse({"error": str(error)}, status=500)

def get_client_ip(request):
    """Get client IP with X-Forwarded-For support"""
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    return x_forwarded_for.split(',')[0] if x_forwarded_for else request.META.get('REMOTE_ADDR')

@csrf_exempt
def view_conversation(request, contact_id):
    try:
        # Query conversations for a specific contact_id
        source = request.GET.get('source', '')
        bpid = request.GET.get('bpid')
        tenant_id = request.headers.get('X-Tenant-Id')

        conversations = Conversation.objects.filter(contact_id=contact_id,business_phone_number_id=bpid,source=source).values('message_text', 'sender', 'encrypted_message_text').order_by('date_time')

        tenant = Tenant.objects.get(id = tenant_id)
        encryption_key = tenant.key
        # print("ENC KEY: ", tenant_id)

        # Format data as per your requirement
        formatted_conversations = []
        for conv in conversations:
            text_to_append = conv.get('message_text', None)
            encrypted_text = conv.get('encrypted_message_text', None)
            # print("text: ", text)

            if encrypted_text!= None:
                encrypted_text = encrypted_text.tobytes()
                decrypted_text = decrypt_data(encrypted_text, key=encryption_key)
                # print("Decrypted Text: ", decrypted_text)
                if decrypted_text:
                    text_to_append = json.dumps(decrypted_text)
                    if text_to_append.startswith('"') and text_to_append.endswith('"'):
                        text_to_append = text_to_append[1:-1]
            # print("Text to append: ", text_to_append, type(text_to_append))
            formatted_conversations.append({'text': text_to_append, 'sender': conv['sender']})

        return JsonResponse(formatted_conversations, safe=False)

    except Exception as e:
        print("Error while fetching conversation data:", e)
        return JsonResponse({'error': str(e)}, status=500)


def is_encrypted(data):
    return data.startswith('b"')



from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.backends import default_backend
import json

def decrypt_data(encrypted_data, key):
    # Extract the IV from the first 16 bytes  # Assuming it's still in string format
    # print("rcvd data: ", encrypted_data)
    # print(type(encrypted_data))

    # Correctly extract IV (first 16 bytes) and the actual encrypted data
    iv = encrypted_data[:16]
    encrypted_data = encrypted_data[16:]

    # Ensure the key is in bytes (handle memoryview if needed)
    if isinstance(key, memoryview):
        key = bytes(key)


    # Initialize the cipher
    cipher = Cipher(algorithms.AES(key), modes.CBC(iv), backend=default_backend())
    decryptor = cipher.decryptor()

    # Perform decryption
    decrypted_data = decryptor.update(encrypted_data) + decryptor.finalize()

    # Remove padding (PKCS#7 padding)
    pad_len = decrypted_data[-1]
    decrypted_data = decrypted_data[:-pad_len]

    return json.loads(decrypted_data.decode())



class GroupViewSet(viewsets.ModelViewSet):
    queryset = Group.objects.all()
    serializer_class = GroupSerializer

    def list(self, request):
        """
        Handle GET requests to retrieve all Group entries.
        """
        queryset = self.get_queryset()
        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)

    def retrieve(self, request, pk=None):
        """
        Handle GET requests to retrieve a single Group entry by ID.
        """
        group = self.get_object()
        serializer = self.get_serializer(group)
        return Response(serializer.data)

    def create(self, request):
        """
        Handle POST requests to create a new Group entry.
        """
        serializer = self.get_serializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def update(self, request, pk=None):
        """
        Handle PUT requests to update a Group entry by ID.
        """
        group = self.get_object()
        serializer = self.get_serializer(group, data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def destroy(self, request, pk=None):
        """
        Handle DELETE requests to delete a Group entry by ID.
        """
        group = self.get_object()
        group.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)
