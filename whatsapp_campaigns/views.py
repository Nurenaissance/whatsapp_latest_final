


from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from django.shortcuts import get_object_or_404
from .models import WhatsappCampaign
from tenant.models import Tenant
from rest_framework.parsers import JSONParser

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
        data = request.data
        tenant_id = request.headers.get("X-Tenant-Id")
        tenant = get_object_or_404(Tenant, id=tenant_id) if tenant_id else None

        campaign = WhatsappCampaign.objects.create(
            name=data["name"],
            bpid=data["bpid"],
            access_token=data["access_token"],
            account_id=data["account_id"],
            tenant=tenant,
            phone=data["phone"],
            templates_data=data["templates_data"]
        )
        return Response({
            "message": "Campaign created successfully!",
            "id": campaign.id
        }, status=status.HTTP_201_CREATED)

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

