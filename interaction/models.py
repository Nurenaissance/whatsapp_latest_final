from django.db import models
from django.contrib.contenttypes.models import ContentType
from django.contrib.contenttypes.fields import GenericForeignKey
from tenant.models import Tenant 
from django.utils import timezone
from contacts.models import Contact
from simplecrm.models import CustomUser

# we are using it, it stores all the conversation happening to our bot 
class Conversation(models.Model):
    contact_id = models.CharField(max_length=255)
    message_text = models.TextField(null=True, blank=True)
    encrypted_message_text = models.BinaryField(null=True, blank=True)
    sender = models.CharField(max_length=50)
    tenant = models.ForeignKey(Tenant, on_delete=models.CASCADE, null=True, blank=True)
    source=models.CharField(max_length=255)
    date_time = models.DateTimeField(null=True, blank=True)
    business_phone_number_id = models.CharField(max_length = 255, null=True, blank=True)
    mapped = models.BooleanField(default=False) 
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE, blank=True, null=True,related_name='interaction_conversations')

    # Add any other file
    # lds you may need

    # Assuming you have tenant-specific tables, add a foreign key to connect them
    # tenant = models.ForeignKey(Tenant, on_delete=models.CASCADE) 

    def __str__(self):
        return f"Conversation ID: {self.id}, Contact ID: {self.contact_id}, Sender: {self.sender}"


# not using
class Group(models.Model):
    name = models.CharField(max_length=255)
    members = models.ManyToManyField(Contact, related_name='groups')
    date_created = models.DateTimeField(auto_now_add=True)
    tenant = models.ForeignKey(Tenant, on_delete=models.CASCADE, null=True, blank=True)
    
    def __str__(self):
        return f"Group ID: {self.id}, Name: {self.name}, Members: {self.members.count()}"

