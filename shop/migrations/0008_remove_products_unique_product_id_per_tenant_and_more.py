# Generated by Django 4.1 on 2024-12-27 08:58

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("shop", "0007_alter_products_image_link_alter_products_product_id_and_more"),
    ]

    operations = [
        migrations.RemoveConstraint(
            model_name="products",
            name="unique_product_id_per_tenant",
        ),
        migrations.RemoveField(
            model_name="products",
            name="product_id",
        ),
        migrations.AlterField(
            model_name="products",
            name="id",
            field=models.CharField(max_length=255, primary_key=True, serialize=False),
        ),
        migrations.AddConstraint(
            model_name="products",
            constraint=models.UniqueConstraint(
                fields=("id", "tenant"), name="unique_product_id_per_tenant"
            ),
        ),
    ]