from rest_framework import generics
from .models import SentimentAnalysis,Conversation
from .insta_msg import group_conversations_into_conversations
from rest_framework.response import Response
from rest_framework import status
from rest_framework.views import APIView

from django.utils import timezone
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
from django.utils import timezone

from simplecrm.models import CustomUser
#from .sentiment_pipeline import analyze_sentiment
from django.views.decorators.csrf import csrf_exempt

from .serializers import (
    SentimentAnalysisSerializer,
    ConversationSerializer,
)

# Sentiment Analysis Views
class SentimentAnalysisListCreateView(generics.ListCreateAPIView):
    queryset = SentimentAnalysis.objects.all()
    serializer_class = SentimentAnalysisSerializer

class SentimentAnalysisDetailView(generics.RetrieveUpdateDestroyAPIView):
    queryset = SentimentAnalysis.objects.all()
    serializer_class = SentimentAnalysisSerializer

# Conversation Views
class ConversationListCreateView(generics.ListCreateAPIView):
    queryset = Conversation.objects.all()
    serializer_class = ConversationSerializer

class ConversationDetailView(generics.RetrieveUpdateDestroyAPIView):
    queryset = Conversation.objects.all()
    serializer_class = ConversationSerializer

class GroupMessagesView(generics.GenericAPIView):
    def post(self, request, *args, **kwargs):
        try:
            tenant_id = request.headers.get('X-Tenant-Id')  # Extract tenant ID from headers
            if not tenant_id:
                return Response({"error": "Missing X-Tenant-Id header."}, status=status.HTTP_400_BAD_REQUEST)
            
            group_conversations_into_conversations(tenant_id)  # Call the function to group messages
            return Response({"message": "Messages grouped into conversations successfully."}, status=status.HTTP_200_OK)
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
