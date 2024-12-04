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
from django.views.decorators.csrf import csrf_exempt
import json
from django.views.decorators.http import require_http_methods

import re
import logging
logger = logging.getLogger('simplecrm')

import json
import logging
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from azure.core.exceptions import AzureError
import redis

# Azure Redis configuration
AZURE_REDIS_HOST = 'whatsappnuren.redis.cache.windows.net'
AZURE_REDIS_PORT = 6379
AZURE_REDIS_PASSWORD = 'O6qxsVvcWHfbwdgBxb1yEDfLeBv5VBmaUAzCaJvnELM='
AZURE_REDIS_SSL = True

redis_client = redis.Redis(
    host=AZURE_REDIS_HOST,
    port=AZURE_REDIS_PORT,
    password=AZURE_REDIS_PASSWORD,
    ssl=AZURE_REDIS_SSL
)

logger = logging.getLogger(__name__)

@csrf_exempt
def save_conversations(request, contact_id):
    try:
        # Rate limiting
        client_ip = _get_client_ip(request)
        rate_limit_key = f'conversations_ratelimit:{client_ip}'
        
        request_count = redis_client.incr(rate_limit_key)
        if request_count == 1:
            redis_client.expire(rate_limit_key, 60)  # Expire after 1 minute
        
        if request_count > 100:
            return JsonResponse({'error': 'Rate limit exceeded'}, status=429)

        if request.method != 'POST':
            return JsonResponse({"error": "Invalid request method"}, status=400)

        source = request.GET.get('source', '')
        body = json.loads(request.body)
        conversations = body.get('conversations', [])
        tenant = body.get('tenant')
        bpid = body.get('business_phone_number_id')

        # Queue conversations for async processing
        from .tasks import process_conversations
        process_conversations.delay({
            'contact_id': contact_id,
            'conversations': conversations,
            'tenant': tenant,
            'source': source,
            'business_phone_number_id': bpid
        })

        return JsonResponse({"message": "Conversations queued for processing"}, status=202)

    except json.JSONDecodeError as e:
        logger.error(f"JSON decode error: {e}")
        return JsonResponse({'error': 'Invalid JSON format'}, status=400)
    except AzureError as e:
        logger.error(f"Azure Redis error: {e}")
        return JsonResponse({'error': 'Cache service unavailable'}, status=503)
    except Exception as e:
        logger.error(f"Unexpected error in whatsapp convo post: {e}")
        return JsonResponse({"error": str(e)}, status=500)

def _get_client_ip(request):
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
