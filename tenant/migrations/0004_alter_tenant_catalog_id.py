# Generated by Django 4.1 on 2024-11-05 13:35

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('tenant', '0003_tenant_catalog_id'),
    ]

    operations = [
        migrations.AlterField(
            model_name='tenant',
            name='catalog_id',
            field=models.BigIntegerField(blank=True, null=True),
        ),
    ]