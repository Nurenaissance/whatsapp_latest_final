from django.db import models
from django.conf import settings
from django.contrib.auth.models import User
from contacts.models import Contact
from tenant.models import Tenant

class NodeTemplate(models.Model):
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True, null=True)
    date_created = models.DateTimeField(auto_now_add=True)
    category = models.CharField(max_length=100)
    createdBy = models.ForeignKey(settings.AUTH_USER_MODEL, related_name='node_temp_createdby', on_delete=models.CASCADE,null=True)
    node_data = models.JSONField()
    fallback_msg = models.TextField(blank=True, null=True)
    fallback_count = models.PositiveIntegerField(blank=True, null=True)
    tenant = models.ForeignKey(Tenant, on_delete=models.CASCADE, null = True, blank=True)

    def __str__(self):
        return self.name 

class Flow(models.Model):
    nodes = models.JSONField(default=list)
    adj_list = models.JSONField(default=list)
    contact = models.ForeignKey(Contact, on_delete=models.CASCADE, null=True, blank=True)
    curr_node = models.IntegerField(default=0)
    ai_mode = models.BooleanField(default=False)