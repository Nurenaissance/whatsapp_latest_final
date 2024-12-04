import os
from simplecrm.celery import Celery

# Set the default Django settings module
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'simplecrm.settings')

app = Celery('simplecrm')
app.config_from_object('django.conf:settings', namespace='CELERY')
app.autodiscover_tasks()