# Generated by Django 4.1 on 2025-01-31 07:18

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("subscriptions", "0009_subscription2"),
    ]

    operations = [
        migrations.AddField(
            model_name="subscription2",
            name="payment_url",
            field=models.URLField(blank=True, null=True),
        ),
    ]
