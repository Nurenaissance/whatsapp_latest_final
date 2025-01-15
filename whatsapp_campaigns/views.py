


from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from django.shortcuts import get_object_or_404
from .models import WhatsappCampaign
from tenant.models import Tenant
from rest_framework.parsers import JSONParser
from whatsapp_chat.models import WhatsappTenantData

class WhatsappCampaignView(APIView):
    """
    Handle CRUD operations for WhatsappCampaign.
    """
    parser_classes = [JSONParser]

    def get(self, request, *args, **kwargs):
        """
        Retrieve all campaigns or a specific campaign by ID.
        """
        campaign_id = request.query_params.get('id', None)
        if campaign_id:
            campaign = get_object_or_404(WhatsappCampaign, id=campaign_id)
            return Response({
                "id": campaign.id,
                "name": campaign.name,
                "bpid": campaign.bpid,
                "access_token": campaign.access_token,
                "account_id": campaign.account_id,
                "tenant_id": campaign.tenant.id,
                "phone": campaign.phone,
                "templates_data": campaign.templates_data
            }, status=status.HTTP_200_OK)

        campaigns = WhatsappCampaign.objects.all()
        data = [
            {
                "id": campaign.id,
                "name": campaign.name,
                "bpid": campaign.bpid,
                "access_token": campaign.access_token,
                "account_id": campaign.account_id,
                "tenant_id": campaign.tenant.id,
                "phone": campaign.phone,
                "templates_data": campaign.templates_data
            }
            for campaign in campaigns
        ]
        return Response(data, status=status.HTTP_200_OK)

    def post(self, request, *args, **kwargs):
        """
        Add a new campaign to the database.
        """
        try:
            # Validate tenant ID
            tenant_id = request.headers.get("X-Tenant-Id")
            if not tenant_id:
                return Response(
                    {"error": "X-Tenant-Id header is required."},
                    status=status.HTTP_400_BAD_REQUEST
                )

            tenant = get_object_or_404(Tenant, id=tenant_id)
            
            # Fetch WhatsApp tenant data
            whatsapp_data = get_object_or_404(WhatsappTenantData, tenant_id=tenant_id)

            # Validate required fields in request data
            required_fields = ["name", "phone", "templates_data"]
            missing_fields = [field for field in required_fields if field not in request.data]
            if missing_fields:
                return Response(
                    {"error": f"Missing required fields: {', '.join(missing_fields)}"},
                    status=status.HTTP_400_BAD_REQUEST
                )

            # Create the campaign
            campaign = WhatsappCampaign.objects.create(
                name=request.data.get("name"),
                bpid=whatsapp_data.business_phone_number_id,
                access_token=whatsapp_data.access_token,
                account_id=whatsapp_data.business_account_id,
                tenant=tenant,
                phone=request.data.get("phone"),
                templates_data=request.data.get("templates_data"),
            )

            return Response(
                {
                    "message": "Campaign created successfully!",
                    "id": campaign.id,
                },
                status=status.HTTP_201_CREATED
            )

        except Exception as e:
            return Response(
                {"error": f"An unexpected error occurred: {str(e)}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    def patch(self, request, *args, **kwargs):
        """
        Update an existing campaign partially.
        """
        campaign_id = request.data.get('id')
        campaign = get_object_or_404(WhatsappCampaign, id=campaign_id)
        
        for key, value in request.data.items():
            if hasattr(campaign, key) and key != 'id':  # Exclude ID
                setattr(campaign, key, value)
        
        campaign.save()
        return Response({
            "message": "Campaign updated successfully!",
            "id": campaign.id
        }, status=status.HTTP_200_OK)

    def delete(self, request, *args, **kwargs):
        """
        Delete a campaign by ID.
        """
        campaign_id = request.query_params.get('id')
        campaign = get_object_or_404(WhatsappCampaign, id=campaign_id)
        campaign.delete()
        return Response({
            "message": "Campaign deleted successfully!"
        }, status=status.HTTP_204_NO_CONTENT)

