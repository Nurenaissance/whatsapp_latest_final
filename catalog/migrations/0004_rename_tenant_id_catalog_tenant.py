# Generated by Django 4.1 on 2024-10-17 11:21

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('catalog', '0003_alter_catalog_catalog_id'),
    ]

    operations = [
        migrations.RenameField(
            model_name='catalog',
            old_name='tenant_id',
            new_name='tenant',
        ),
    ]