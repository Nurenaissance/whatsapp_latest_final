from django.shortcuts import get_object_or_404
from rest_framework import generics, status
from rest_framework.response import Response
from .models import Order, Retailer
from tenant.models import Tenant
from .serializers import OrderSerializer, RetailerSerializer

# Retailer Views
class RetailerCreateAPIView(generics.CreateAPIView):
    queryset = Retailer.objects.all()
    serializer_class = RetailerSerializer

    def perform_create(self, serializer):
        tenant_id = self.request.headers.get('X-Tenant-Id')
        tenant = Tenant.objects.get(id=tenant_id)
        serializer.save(tenant=tenant)

class RetailerUpdateAPIView(generics.UpdateAPIView):
    queryset = Retailer.objects.all()
    serializer_class = RetailerSerializer

class RetailerDeleteAPIView(generics.DestroyAPIView):
    queryset = Retailer.objects.all()
    serializer_class = RetailerSerializer

class RetailerListAPIView(generics.ListAPIView):
    queryset = Retailer.objects.all()
    serializer_class = RetailerSerializer

class RetailerDetailAPIView(generics.RetrieveAPIView):
    queryset = Retailer.objects.all()
    serializer_class = RetailerSerializer

# Order Views
class OrderCreateAPIView(generics.CreateAPIView):
    queryset = Order.objects.all()
    serializer_class = OrderSerializer

    def perform_create(self, serializer):
        tenant_id = self.request.headers.get('X-Tenant-Id')
        tenant = Tenant.objects.get(id=tenant_id)
        serializer.save(tenant=tenant)


class OrderUpdateAPIView(generics.UpdateAPIView):
    queryset = Order.objects.all()
    serializer_class = OrderSerializer

class OrderDeleteAPIView(generics.DestroyAPIView):
    queryset = Order.objects.all()
    serializer_class = OrderSerializer

class OrderListAPIView(generics.ListAPIView):
    queryset = Order.objects.all()
    serializer_class = OrderSerializer

class OrderDetailAPIView(generics.RetrieveAPIView):
    queryset = Order.objects.all()
    serializer_class = OrderSerializer