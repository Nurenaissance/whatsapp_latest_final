from rest_framework import serializers
from .models import userData

class PromptSerializer(serializers.Serializer):
    prompt = serializers.CharField(max_length=1000)

class userDataSerializer(serializers.ModelSerializer):
    class Meta:
        model = userData
        fields = "__all__"

    