from rest_framework import serializers
from .models import Plan, Subscription2, Subscription

class PlanSerializer(serializers.ModelSerializer):
    class Meta:
        model = Plan
        fields = '__all__'  # Include all fields

class SubscriptionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Subscription
        fields = '__all__'  # Include all fields

class Subscription2Serializer(serializers.ModelSerializer):
    class Meta:
        model = Subscription2
        fields = '__all__'  # Include all fields
