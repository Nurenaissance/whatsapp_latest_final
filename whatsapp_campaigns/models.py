from django.db import models
from tenant.models import Tenant

class WhatsappCampaign(models.Model):
    id = models.AutoField(primary_key=True)
    name = models.CharField(max_length=255, null=True, blank=True)
    bpid = models.CharField(max_length=255, null=True, blank=True)
    access_token = models.CharField(max_length=255, null=True, blank=True)
    account_id = models.CharField(max_length=255, null=True, blank=True)
    tenant = models.ForeignKey(Tenant, on_delete=models.CASCADE, null=True, blank=True)
    phone = models.JSONField(null=True, blank=True)
    templates_data = models.JSONField(null=True, blank=True, default=dict)

    def __init__(self, *args, **kwargs):
        super(WhatsappCampaign, self).__init__(*args, **kwargs)

    def __str__(self):
        return self.name