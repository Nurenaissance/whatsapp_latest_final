# Generated by Django 4.1 on 2024-10-08 16:55

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ('contenttypes', '0002_remove_content_type_name'),
        ('contacts', '0001_initial'),
        ('tenant', '__first__'),
    ]

    operations = [
        migrations.CreateModel(
            name='Interaction',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('entity_id', models.PositiveIntegerField()),
                ('interaction_type', models.CharField(choices=[('Call', 'Call'), ('Email', 'Email'), ('Meeting', 'Meeting'), ('Note', 'Note')], max_length=50)),
                ('interaction_datetime', models.DateTimeField()),
                ('notes', models.TextField(blank=True, null=True)),
                ('entity_type', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, to='contenttypes.contenttype')),
                ('tenant', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, to='tenant.tenant')),
            ],
        ),
        migrations.CreateModel(
            name='Group',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=255)),
                ('date_created', models.DateTimeField(auto_now_add=True)),
                ('members', models.ManyToManyField(related_name='groups', to='contacts.contact')),
                ('tenant', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, to='tenant.tenant')),
            ],
        ),
        migrations.CreateModel(
            name='Conversation',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('contact_id', models.CharField(max_length=255)),
                ('message_text', models.TextField()),
                ('sender', models.CharField(max_length=50)),
                ('source', models.CharField(max_length=255)),
                ('date_time', models.DateTimeField(auto_now=True)),
                ('business_phone_number_id', models.CharField(blank=True, max_length=255, null=True)),
                ('mapped', models.BooleanField(default=False)),
                ('tenant', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, to='tenant.tenant')),
            ],
        ),
    ]