# Generated by Django 4.1 on 2024-10-09 06:46

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('communication', '0001_initial'),
    ]

    operations = [
        migrations.AlterField(
            model_name='conversation',
            name='platform',
            field=models.CharField(choices=[('whatsapp', 'WhatsApp')], max_length=50),
        ),
        migrations.AlterField(
            model_name='conversation',
            name='user',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='communication_conversations', to=settings.AUTH_USER_MODEL),
        ),
        migrations.AlterField(
            model_name='message',
            name='platform',
            field=models.CharField(choices=[('whatsapp', 'WhatsApp')], max_length=50),
        ),
    ]