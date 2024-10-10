from rest_framework import serializers

class QuerySerializer(serializers.Serializer):
    prompt = serializers.CharField()


