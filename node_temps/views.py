from rest_framework import generics, exceptions
from .models import NodeTemplate
from .serializers import NodeTemplateSerializer


class NodeTemplateListCreateAPIView(generics.ListCreateAPIView):
    serializer_class = NodeTemplateSerializer

    def get_queryset(self):

        tenant = self.request.headers.get('X-Tenant-Id')
        if not tenant:
            raise exceptions.ValidationError('Tenant ID is missing from the request headers.')

        queryset = NodeTemplate.objects.filter(tenant_id = tenant)

        return queryset
    
    def perform_create(self, serializer):
        tenant_id = self.request.headers.get('X-Tenant-Id')
        if not tenant_id:
            raise exceptions.ValidationError('Tenant ID is missing in headers')
        
        serializer.save(tenant_id=tenant_id)
    




class NodeTemplateDetailAPIView(generics.RetrieveUpdateDestroyAPIView):
    queryset = NodeTemplate.objects.all()
    serializer_class = NodeTemplateSerializer
