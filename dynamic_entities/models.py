
from django.db import models
from django.conf import settings
from tenant.models import Tenant


class DynamicModel(models.Model):
    model_name = models.CharField(max_length=255)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    tenant = models.ForeignKey(Tenant, on_delete=models.CASCADE, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

class DynamicField(models.Model):
    dynamic_model = models.ForeignKey(DynamicModel, on_delete=models.CASCADE)
    field_name = models.CharField(max_length=255)
    field_type = models.CharField(max_length=50)