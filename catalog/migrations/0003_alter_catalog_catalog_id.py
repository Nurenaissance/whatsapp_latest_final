# Generated by Django 4.1 on 2024-10-16 09:30

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('catalog', '0002_alter_catalog_catalog_id_alter_catalog_currency_and_more'),
    ]

    operations = [
        migrations.AlterField(
            model_name='catalog',
            name='catalog_id',
            field=models.CharField(blank=True, max_length=255, null=True),
        ),
    ]
