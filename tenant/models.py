from django.db import models

class Tenant(models.Model):
    TIER_CHOICES = [
        ('free', 'Free'),
        ('basic', 'Basic'),
        ('pro', 'Pro'),
        ('enterprise', 'Enterprise'),
    ]
    
    id = models.CharField(primary_key=True, max_length=50)
    organization=models.CharField(max_length=100)
    db_user = models.CharField(max_length=100)
    db_user_password = models.CharField(max_length=100)
    spreadsheet_link = models.URLField(null=True, blank=True)
    catalog_id = models.BigIntegerField(null=True, blank=True)
    key = models.BinaryField(null=True, blank=True)
    tier = models.CharField(
        max_length=20, 
        choices=TIER_CHOICES, 
        default='free'
    )
    agents = models.JSONField(null=True, blank=True)

    def __str__(self):
        return self.id

class WA(models.Model):
    tenant = models.ForeignKey(Tenant, on_delete=models.CASCADE)
    access_token = models.CharField(max_length= 100)
    business_phone_number_id = models.DecimalField(max_digits=40, decimal_places=0)
