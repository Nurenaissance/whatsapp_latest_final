# Generated by Django 4.1 on 2024-12-24 12:03

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("whatsapp_chat", "0007_whatsapptenantdata_language"),
    ]

    operations = [
        migrations.AddField(
            model_name="whatsapptenantdata",
            name="introductory_msg",
            field=models.CharField(blank=True, max_length=40, null=True),
        ),
    ]