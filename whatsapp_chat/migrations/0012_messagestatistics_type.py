# Generated by Django 4.1 on 2025-01-21 03:29

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("whatsapp_chat", "0011_messagestatistics"),
    ]

    operations = [
        migrations.AddField(
            model_name="messagestatistics",
            name="type",
            field=models.CharField(max_length=50, null=True),
        ),
    ]
