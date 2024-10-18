from django.db import models
from tenant.models import Tenant
class Catalog(models.Model):
    product_retailer_id = models.CharField(max_length=255, unique=True)  # Unique ID for the product retailer
    product_name = models.CharField(max_length=255, null=True, blank=True)
    description = models.TextField(null=True, blank=True)
    item_price = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    currency = models.CharField(max_length=3, null=True, blank=True)
    tenant = models.ForeignKey(Tenant, on_delete=models.CASCADE, null=True, blank=True)
    catalog_id = models.CharField(max_length=255, null=True, blank=True)
    quantity = models.IntegerField(null=True, blank=True)
    image_url = models.URLField(null=True, blank=True)
    product_url = models.URLField(null=True, blank=True)
    def __str__(self):
        return f"Catalog {self.catalog_id} - Product {self.product_retailer_id} - {self.product_name}"

    class Meta:
        verbose_name = "Catalog"
        verbose_name_plural = "Catalogs"