# Generated by Django 4.1 on 2024-12-27 09:11

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ("shop", "0009_remove_products_unique_product_id_per_tenant_and_more"),
    ]

    operations = [
        migrations.RemoveConstraint(
            model_name="products",
            name="unique_title_per_tenant",
        ),
    ]
