# Generated by Django 4.1 on 2024-10-08 16:34

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ('contenttypes', '0002_remove_content_type_name'),
        ('tenant', '__first__'),
    ]

    operations = [
        migrations.CreateModel(
            name='CustomField',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('model_name', models.CharField(choices=[('account', 'Account'), ('calls', 'calls'), ('lead', 'Lead'), ('interaction', 'Interaction'), ('contact', 'Contact'), ('product', 'Product'), ('vendors', 'Vendors')], max_length=20)),
                ('custom_field', models.CharField(max_length=255)),
                ('value', models.TextField(blank=True, null=True)),
                ('field_type', models.CharField(choices=[('char', 'CharField'), ('text', 'TextField'), ('int', 'IntegerField'), ('float', 'FloatField'), ('bool', 'BooleanField'), ('date', 'DateField'), ('datetime', 'DateTimeField'), ('email', 'EmailField'), ('url', 'URLField')], max_length=20)),
                ('object_id', models.PositiveIntegerField()),
                ('content_type', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='custom_fields', to='contenttypes.contenttype')),
                ('tenant', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='tenant.tenant')),
            ],
        ),
    ]