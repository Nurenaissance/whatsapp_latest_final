# Generated by Django 4.1 on 2024-12-09 11:27

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('interaction', '0005_alter_conversation_date_time'),
    ]

    operations = [
        migrations.AddField(
            model_name='conversation',
            name='encrypted_message_text',
            field=models.BinaryField(blank=True, null=True),
        ),
    ]