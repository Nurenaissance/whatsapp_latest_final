from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from .serializers import PromptSerializer, userDataSerializer
from .models import userData
from django.db import connection
from openai import OpenAI
import os
from rest_framework import generics


class userCreateListView(generics.ListCreateAPIView):
    queryset = userData.objects.all()
    serializer_class = userDataSerializer
    # permission_classes = (AllowAny,)

class userDetailAPIView(generics.RetrieveUpdateDestroyAPIView):
    queryset = userData.objects.all()
    serializer_class = userDataSerializer

    def get_queryset(self):
        tenant_id = self.request.headers.get('X-Tenant-Id')
        if tenant_id:
            return userData.objects.filter(tenant__id=tenant_id)
        return userData.objects.none()  