from django.db import models
from tenant.models import Tenant
class Catalog(models.Model):
    product_retailer_id = models.CharField(max_length=255, unique=True)  # Unique ID for the product retailer
    product_name = models.CharField(max_length=255)  # Name of the product
    description = models.TextField(null=True, blank=True)  # Detailed description of the product
    item_price = models.DecimalField(max_digits=10, decimal_places=2)  # Price of the item
    currency = models.CharField(max_length=3)  # Currency of the price (e.g., USD, EUR)
    tenant_id = models.ForeignKey(Tenant, on_delete=models.CASCADE)  # Foreign key for tenant
    catalog_id = models.CharField(max_length=255, unique=True)  # Catalog identifier
    quantity = models.IntegerField()  # Quantity of the product in the catalog
    image_url = models.URLField(null=True, blank=True)  # URL for the product image
    product_url = models.URLField(null=True, blank=True)  # URL to a product page or marketplace

    def __str__(self):
        return f"Catalog {self.catalog_id} - Product {self.product_retailer_id} - {self.product_name}"

    class Meta:
        verbose_name = "Catalog"
        verbose_name_plural = "Catalogs"