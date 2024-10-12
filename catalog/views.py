from django.shortcuts import render
from .models import Catalog
from .seriliazers import CatalogSerializer
from rest_framework import generics, exceptions
from tenant.models import Tenant

# Create your views here.
class CatalogListCreateAPIView(generics.ListCreateAPIView):
    queryset = Catalog.objects.all()
    serializer_class = CatalogSerializer

    def get_queryset(self):
        tenant_id = self.request.headers.get('X-Tenant-Id')
        return Catalog.objects.filter(tenant_id=tenant_id)

    def perform_create(self, serializer):
        tenant_id = self.request.headers.get('X-Tenant-Id')

        try:
            tenant = Tenant.objects.get(id=tenant_id)
        except Tenant.DoesNotExist:
            raise exceptions.NotFound("Tenant not found.")
        
        serializer.save(tenant_id=tenant)
        super().perform_create(serializer)

