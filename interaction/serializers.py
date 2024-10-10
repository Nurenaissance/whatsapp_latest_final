from rest_framework import serializers
from .models import Conversation, Group


class WhatsappCSerializer(serializers.ModelSerializer):
    class Meta:
        model = Conversation
        fields = "__all__"

class GroupSerializer(serializers.ModelSerializer):
    class Meta:
        model = Group
        fields = ['id', 'name', 'members', 'date_created', 'tenant']

class ConversationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Conversation
        fields = '__all__'