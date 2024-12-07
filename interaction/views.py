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
import json
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
from django.db import transaction

from celery import shared_task
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

@shared_task(bind=True, max_retries=3, rate_limit='100/m')
def process_conversations(self, payload: Dict):
    try:
        print("views process conversations")
        with transaction.atomic():
            # Batch insert with chunk processing
            conversations_to_create = create_conversation_objects(payload)
            bulk_create_with_batching(conversations_to_create)
    except Exception as exc:
        # Exponential backoff with jitter for better distributed retry
        self.retry(exc=exc, countdown=2 ** self.request.retries + random.uniform(0, 1))

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

@csrf_exempt
def save_conversations(request, contact_id):
    try:
        # Enhanced rate limiting with sliding window
        print("checking rate limit")
        if not check_rate_limit(request):
            return JsonResponse({'error': 'Rate limit exceeded'}, status=429)
        print("Starting")
        payload = extract_payload(request)
        if 'time' in payload:
            raw_time = payload['time']
            
            # Remove commas
            sanitized_time = raw_time.replace(",", "")
            
            try:
                # Convert to integer and then to seconds
                timestamp_seconds = int(sanitized_time) / 1000
                
                # Convert to PostgreSQL timestamp format
                postgres_timestamp = datetime.fromtimestamp(timestamp_seconds)
                postgres_timestamp = make_aware(postgres_timestamp)
                
                payload['time'] = postgres_timestamp
                
            except ValueError as e:
                print(f"Error processing time: {e}")

        print("payload: ", payload)

        # Asynchronous processing with error tracking
        process_conversations.delay(payload)
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
        conversations = Conversation.objects.filter(contact_id=contact_id,business_phone_number_id=bpid,source=source).values('message_text', 'sender').order_by('date_time')

        # Format data as per your requirement
        formatted_conversations = []
        for conv in conversations:
            formatted_conversations.append({'text': conv['message_text'], 'sender': conv['sender']})

        return JsonResponse(formatted_conversations, safe=False)

    except Exception as e:
        print("Error while fetching conversation data:", e)
        return JsonResponse({'error': str(e)}, status=500)


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
