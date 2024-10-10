from django.db import models
from django.contrib.auth.models import User
from django.conf import settings
from tenant.models import Tenant 

class Contact(models.Model):
    name = models.CharField("name", max_length=255, null=True, blank=True)
    email = models.EmailField(null=True, blank=True)
    phone = models.CharField(max_length=20, null=True, blank=True)
    address = models.TextField(blank=True, null=True)
    description = models.TextField(blank=True, null=True)
    createdBy = models.ForeignKey(settings.AUTH_USER_MODEL, related_name='contact_created_by', on_delete=models.CASCADE, null=True, blank=True)
    createdOn = models.DateTimeField("Created on", auto_now_add=True, null=True, blank=True)
    isActive = models.BooleanField(default=False, null=True, blank=True)
    tenant = models.ForeignKey(Tenant, on_delete=models.CASCADE, null=True, blank=True)
    bg_id = models.CharField(max_length=50, null=True, blank=True)
    bg_name = models.CharField(max_length=50, null=True, blank=True)
    
    def __str__(self):
        return self.name or ''