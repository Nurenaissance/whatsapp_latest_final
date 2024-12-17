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

from django.core.exceptions import ValidationError
from .models import NodeTemplate

def saveFlow(flow_data):
    """
    Saves or updates a NodeTemplate flow in the database.
    
    Parameters:
        flow_data (dict): Data containing the flow details, including 'tenant_id' and 'node_data'.

    Returns:
        NodeTemplate: The saved or updated NodeTemplate object.
    """
    tenant_id = flow_data.get('tenant_id')
    if not tenant_id:
        raise ValidationError("Tenant ID is required to save the flow.")
    
    node_data = flow_data.get('node_data')
    if not node_data:
        raise ValidationError("Flow data (node_data) is required to save the flow.")
    
    # Optional fields
    name = flow_data.get('name', 'Prompt Flow')
    description = flow_data.get('description', '')
    fallback_msg = flow_data.get('fallback_msg', '')
    fallback_count = flow_data.get('fallback_count', 0)
    category = flow_data.get('category', None)  # Can be None if category is optional

    # Check if this is an update or create operation
    node_id = flow_data.get('id')
    if node_id:
        # Update existing NodeTemplate
        try:
            node_template = NodeTemplate.objects.get(id=node_id, tenant_id=tenant_id)
            node_template.name = name
            node_template.description = description
            node_template.node_data = node_data
            node_template.fallback_msg = fallback_msg
            node_template.fallback_count = fallback_count
            node_template.category = category
            node_template.save()
        except NodeTemplate.DoesNotExist:
            raise ValidationError(f"No NodeTemplate found with ID {node_id} for tenant {tenant_id}.")
    else:
        # Create a new NodeTemplate
        node_template = NodeTemplate.objects.create(
            name=name,
            description=description,
            node_data=node_data,
            fallback_msg=fallback_msg,
            fallback_count=fallback_count,
            tenant_id=tenant_id,
            category=category
        )
    
    return node_template
