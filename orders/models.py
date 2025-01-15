from django.db import models
from tenant.models import Tenant


class Retailer(models.Model):
    name = models.CharField(max_length=255, db_index=True)
    email = models.EmailField(unique=True, db_index=True)
    phone_number = models.CharField(max_length=20, unique=True, db_index=True)
    tenant = models.ForeignKey(Tenant, on_delete=models.CASCADE, null=True, blank=True)


    def __str__(self):
        return self.name

class Order(models.Model):
    tenant = models.ForeignKey(Tenant, on_delete=models.CASCADE, null=True, blank=True)
    items = models.JSONField()
    total = models.FloatField()
    status = models.CharField(max_length=50, db_index=True)
    order_datetime = models.DateTimeField(auto_now=True)
    shipping_address = models.CharField(max_length=255, null=True, blank=True)
    payment_method = models.CharField(max_length=50, null=True, blank=True)

    def __str__(self):
        return f"Order {self.id} for {self.retailer.name}"