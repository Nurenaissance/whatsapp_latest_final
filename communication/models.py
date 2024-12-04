from django.db import models
from simplecrm.models import CustomUser
from contacts.models import Contact

class SentimentAnalysis(models.Model):
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE, null=True, blank=True)
    conversation_id = models.IntegerField()
    joy_score = models.FloatField()
    sadness_score = models.FloatField()
    anger_score = models.FloatField()
    trust_score = models.FloatField()
    dominant_emotion = models.CharField(max_length=50)  
    timestamp = models.DateTimeField(auto_now_add=True)
    contact_id = models.ForeignKey(Contact, on_delete=models.CASCADE)


class Conversation(models.Model):
    PLATFORM_CHOICES = [
        ('whatsapp', 'WhatsApp'),
    ]
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE, blank=True, null=True,related_name='communication_conversations')
    conversation_id = models.CharField(max_length=255, unique=True)
    messages = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    platform = models.CharField(max_length=50, choices=PLATFORM_CHOICES)
    contact_id = models.ForeignKey(Contact, on_delete=models.CASCADE)
