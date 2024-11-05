from rest_framework import serializers
from .models import Products


class ShopSerializer(serializers.ModelSerializer):
    class Meta:
        model = Products
        exclude = ['catalog']

    def create(self, validated_data):
        if isinstance(validated_data, list):
            print(f"Creating multiple items: {validated_data}")
            return Products.objects.bulk_create([Products(**item) for item in validated_data])
        print(f"Creating single item: {validated_data}")
        return super().create(validated_data)