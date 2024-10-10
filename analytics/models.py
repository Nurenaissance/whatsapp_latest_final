from django.db import models
from tenant.models import Tenant

class FAISSIndex(models.Model):
    name = models.CharField(max_length=100)
    index_data = models.BinaryField()
    json_data = models.JSONField(null=True, blank=True)
    tenant = models.ForeignKey(Tenant, on_delete=models.CASCADE, null=True, blank=True)

class userData(models.Model):
    name = models.CharField(max_length=50, null=True, blank=True)
    phone = models.BigIntegerField()
    doc_name = models.CharField(max_length=100)
    data = models.JSONField()
    tenant = models.ForeignKey(Tenant, on_delete=models.CASCADE, null=True, blank=True)
