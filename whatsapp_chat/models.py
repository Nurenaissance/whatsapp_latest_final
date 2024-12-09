from django.db import models
from tenant.models import Tenant 
from contacts.models import Contact

class WAConversation(models.Model):
    contact_id = models.CharField(max_length=255)
    message_text = models.TextField()
    sender = models.CharField(max_length=50)
    tenant = models.ForeignKey(Tenant, on_delete=models.CASCADE)
    source=models.CharField(max_length=255)
    timestamp = models.DateTimeField(auto_now_add=True)
    # Add any other fields you may need

    # Assuming you have tenant-specific tables, add a foreign key to connect them
    # tenant = models.ForeignKey(Tenant, on_delete=models.CASCADE) 

    def __str__(self):
        return f"Conversation ID: {self.id}, Contact ID: {self.contact_id}, Sender: {self.sender}"


class WhatsappTenantData(models.Model):
    business_phone_number_id = models.BigIntegerField(primary_key=True)
    flow_data = models.JSONField(null=True, blank=True)
    adj_list = models.JSONField(null=True, blank=True)
    access_token = models.CharField(max_length=300)
    updated_at = models.DateTimeField(auto_now=True)
    business_account_id = models.BigIntegerField()
    start = models.IntegerField(null=True, blank=True)
    fallback_count = models.IntegerField(null=True, blank=True)
    fallback_message = models.CharField(max_length=1000, null=True, blank=True)
    flow_name = models.CharField(max_length=200, null=True, blank=True)
    tenant = models.ForeignKey(Tenant, on_delete=models.CASCADE)
    spreadsheet_link = models.URLField(blank=True, null=True)