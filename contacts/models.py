from django.db import models
from django.contrib.auth.models import User
from django.conf import settings
from tenant.models import Tenant 

class Contact(models.Model):
    name = models.CharField("name", max_length=255, null=True, blank=True)
    email = models.EmailField(null=True, blank=True)
    phone = models.CharField(max_length=20)
    address = models.TextField(blank=True, null=True)
    description = models.TextField(blank=True, null=True)
    createdBy = models.ForeignKey(settings.AUTH_USER_MODEL, related_name='contact_created_by', on_delete=models.CASCADE, null=True, blank=True)
    createdOn = models.DateTimeField("Created on", auto_now_add=True, null=True, blank=True)
    isActive = models.BooleanField(default=False, null=True, blank=True)
    tenant = models.ForeignKey(Tenant, on_delete=models.CASCADE, null=True, blank=True)
    template_key = models.CharField(max_length=50, null=True, blank=True)
    last_seen = models.DateTimeField(null=True, blank=True)
    last_delivered = models.DateTimeField(null=True, blank=True)
    last_replied = models.DateTimeField(null=True, blank=True)

    def save(self, *args, **kwargs):
        if self.phone:
            self.phone = str(self.phone) 
            
            if len(self.phone) == 10 and self.phone.isdigit():
                self.phone = f"91{self.phone}"
        super().save(*args, **kwargs)
    
    def __str__(self):
        return f"Name: {self.name}, Phone: {self.phone}, Email: {self.email}, Address: {self.address}, Description: {self.description}, Tenant: {self.tenant}, Created On: {self.createdOn}, Template Key: {self.template_key}"
