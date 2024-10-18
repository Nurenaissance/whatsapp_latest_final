from rest_framework import serializers
from .models import Catalog


class CatalogSerializer(serializers.ModelSerializer):
    class Meta:
        model = Catalog
        fields = '__all__'

    def create(self, validated_data):
        if isinstance(validated_data, list):
            print(f"Creating multiple items: {validated_data}")
            return Catalog.objects.bulk_create([Catalog(**item) for item in validated_data])
        print(f"Creating single item: {validated_data}")
        return super().create(validated_data)
