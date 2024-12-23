from celery import shared_task
from django.db import transaction
import logging
import os, openai, json
from .models import NodeTemplate


logger = logging.getLogger(__name__)

# sendMessage:
# node['data']['fields']['content']['text']
# node['data']['fields']['content']['caption']

# askQuestion:
# node['data']['options']
# node['data']['question']

# setCondition:
# node['data']['condition']


@shared_task(bind=True, max_retries=3)
def add_translations(self, languages, node_temp_id):
    node_template = NodeTemplate.objects.get(id = node_temp_id)
    node_data = node_template.node_data
    nodes = node_data['nodes']