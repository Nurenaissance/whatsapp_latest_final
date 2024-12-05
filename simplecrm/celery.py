import os
from celery import Celery

# Set default Django settings module
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'simplecrm.settings')

# Create Celery app
app = Celery('simplecrm')

# Load configuration from Django settings
app.config_from_object('django.conf:settings', namespace='CELERY')

# Autodiscover tasks from all registered Django apps
app.autodiscover_tasks()

# Add shared_task decorator
def shared_task(*args, **kwargs):
    return app.task(*args, **kwargs)