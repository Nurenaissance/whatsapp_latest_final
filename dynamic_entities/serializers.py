from rest_framework import serializers
from .models import DynamicModel, DynamicField

class DynamicFieldSerializer(serializers.ModelSerializer):
    class Meta:
        model = DynamicField
        fields = ['field_name', 'field_type']

class DynamicModelSerializer(serializers.ModelSerializer):
    fields = DynamicFieldSerializer(many=True)

    class Meta:
        model = DynamicModel
        fields = ['model_name', 'fields']

    def create(self, validated_data):
        fields_data = validated_data.pop('fields')
        dynamic_model = DynamicModel.objects.create(**validated_data)
        for field_data in fields_data:
            DynamicField.objects.create(dynamic_model=dynamic_model, **field_data)
        return dynamic_model
