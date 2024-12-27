from django.db import models
from tenant.models import Tenant

class Catalog(models.Model):
    catalogue_id = models.BigIntegerField(primary_key=True)
    tenant = models.ForeignKey(Tenant, on_delete=models.CASCADE, null=True, blank=True)

    def __str__(self):
        return f"Catalog {self.catalog_id} - Product {self.product_retailer_id} - {self.product_name}"

    class Meta:
        verbose_name = "Catalog"
        verbose_name_plural = "Catalogs"

class Products(models.Model):

    PRODUCT_CONDITION = [
        ('new', 'new'),
        ('refurbished', 'refurbished'),
        ('used', 'used'),
    ]
    PRODUCT_AVAL = [
        ('in_stock', 'in_stock'),
        ('out_of_stock', 'out_of_stock')
    ]

    product_id = models.CharField(max_length=255)
    title = models.CharField(max_length=255)
    description = models.TextField()
    link = models.URLField()
    image_link = models.URLField(max_length=300)
    condition = models.CharField(choices=PRODUCT_CONDITION, default='new', max_length=255)
    availability = models.CharField(choices=PRODUCT_AVAL, default='in stock', max_length=255)
    price = models.IntegerField()
    quantity = models.IntegerField()
    brand = models.CharField(max_length=255)
    catalog = models.ForeignKey(Catalog, on_delete=models.CASCADE, null=True, blank=True)
    status = models.CharField(max_length=50, default="active")
    tenant = models.ForeignKey(Tenant, on_delete=models.CASCADE, null=True, blank=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=['product_id', 'tenant'], name='unique_product_id_per_tenant'),
            models.UniqueConstraint(fields=['title', 'tenant'], name='unique_title_per_tenant'),
            # models.UniqueConstraint(fields=['image_link', 'tenant'], name='unique_image_link_per_tenant'),
        ]