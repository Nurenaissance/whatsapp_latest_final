# Generated by Django 4.1 on 2025-01-07 03:51

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("orders", "0003_remove_order_retailer_order_tenant"),
    ]

    operations = [
        migrations.AlterField(
            model_name="order",
            name="total",
            field=models.FloatField(),
        ),
    ]
