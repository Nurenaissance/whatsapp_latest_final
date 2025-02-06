from django.db import models
from tenant.models import Tenant

class Flows(models.Model):
    id = models.CharField( max_length=20 ,primary_key=True)
    name = models.CharField(max_length=50)
    flow_json = models.JSONField(null=True, blank=True)
    publish = models.BooleanField()
    tenant = models.ForeignKey(Tenant, on_delete=models.CASCADE)