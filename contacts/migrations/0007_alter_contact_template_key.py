# Generated by Django 4.1 on 2024-12-23 10:41

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("contacts", "0006_remove_contact_bg_id_remove_contact_bg_name_and_more"),
    ]

    operations = [
        migrations.AlterField(
            model_name="contact",
            name="template_key",
            field=models.JSONField(blank=True, null=True),
        ),
    ]