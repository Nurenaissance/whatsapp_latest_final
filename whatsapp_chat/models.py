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
    id = models.AutoField(primary_key=True)
    business_phone_number_id = models.BigIntegerField(primary_key=False)
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
    language = models.CharField(max_length=20, default='en')
    introductory_msg = models.JSONField(null=True, blank=True)
    multilingual = models.BooleanField(default=False)

class MessageStatistics(models.Model):
    id = models.AutoField(primary_key=True)
    name = models.CharField(max_length=255, null=True)
    sent = models.IntegerField(default=0)
    delivered = models.IntegerField(default=0)
    read = models.IntegerField(default=0)
    replied = models.IntegerField(default=0)
    failed = models.IntegerField(default=0)
    tenant_id = models.CharField(max_length=50, null=True)
    type = models.CharField(max_length=50, null=True)


    def __str__(self):
        return f"{self.name} - {self.tenant_id}"

class IndividualMessageStatistics(models.Model):

    STATUS_CHOICES = [
        ('sent', 'Sent'),
        ('read', 'Read'),
        ('delivered', 'Delivered'),
        ('failed', 'Failed'),
        ('replied', 'Replied'),
    ]

    TYPE_CHOICES = [
        ('campaign', 'Campaign'),
        ('template', 'Template'),
        ('group', 'Broadcast Group'),
    ]

    id = models.AutoField(primary_key=True)
    message_id = models.CharField(max_length=255, null=True)
    status = models.CharField(max_length=50, choices=STATUS_CHOICES, null=True)
    type = models.CharField(max_length=50, choices=TYPE_CHOICES, null=True)
    type_identifier = models.CharField(
        max_length=255, 
        null=True, 
        help_text="Identifier based on the type: Campaign ID, Template Name, or Group ID."
    )
    template_name = models.CharField(
        max_length=255,
        null=True,
        blank=True,
        help_text="The name of the template (if applicable)."
    )
    userPhone = models.CharField(max_length=15, null=True, help_text="User's phone number in international format.")
    tenant_id = models.CharField(max_length=20, null=True, help_text="ID of the tenant associated with this message.")
    bpid = models.CharField(max_length=255, null=True, help_text="Business process ID associated with the message.")
    timestamp = models.DateTimeField(auto_now_add=True, help_text="Timestamp when the message record was created.")

    def __str__(self):
        return f"Message {self.message_id} - Status: {self.status} - Type: {self.type}"

    def save(self, *args, **kwargs):
        """
        Custom save method to validate fields based on the `type`.
        """
        if self.type == 'campaign' and not self.type_identifier:
            raise ValueError("Campaign type requires a Campaign ID in `type_identifier`.")
        elif self.type == 'template' and (not self.type_identifier or not self.template_name):
            raise ValueError("Template type requires both `type_identifier` and `template_name`.")
        elif self.type == 'group' and not self.type_identifier:
            raise ValueError("Group type requires a Group ID in `type_identifier`.")
        super().save(*args, **kwargs)
