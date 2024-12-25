from rest_framework import generics, exceptions
from .models import NodeTemplate
from .serializers import NodeTemplateSerializer

from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt


class NodeTemplateListCreateAPIView(generics.ListCreateAPIView):
    serializer_class = NodeTemplateSerializer

    def get_queryset(self):

        tenant = self.request.headers.get('X-Tenant-Id')
        if not tenant:
            raise exceptions.ValidationError('Tenant ID is missing from the request headers.')

        queryset = NodeTemplate.objects.filter(tenant_id = tenant)

        return queryset
    
    def perform_create(self, serializer):
        tenant_id = self.request.headers.get('X-Tenant-Id')
        if not tenant_id:
            raise exceptions.ValidationError('Tenant ID is missing in headers')
        
        serializer.save(tenant_id=tenant_id)
    

class NodeTemplateDetailAPIView(generics.RetrieveUpdateDestroyAPIView):
    queryset = NodeTemplate.objects.all()
    serializer_class = NodeTemplateSerializer

from django.core.exceptions import ValidationError
from .models import NodeTemplate

def saveFlow(flow_data):
    """
    Saves or updates a NodeTemplate flow in the database.
    
    Parameters:
        flow_data (dict): Data containing the flow details, including 'tenant_id' and 'node_data'.

    Returns:
        NodeTemplate: The saved or updated NodeTemplate object.
    """
    tenant_id = flow_data.get('tenant_id')
    if not tenant_id:
        raise ValidationError("Tenant ID is required to save the flow.")
    
    node_data = flow_data.get('node_data')
    if not node_data:
        raise ValidationError("Flow data (node_data) is required to save the flow.")
    
    # Optional fields
    name = flow_data.get('name', 'Prompt Flow')
    description = flow_data.get('description', '')
    fallback_msg = flow_data.get('fallback_msg', '')
    fallback_count = flow_data.get('fallback_count', 0)
    category = flow_data.get('category', None)  # Can be None if category is optional

    # Check if this is an update or create operation
    node_id = flow_data.get('id')
    if node_id:
        # Update existing NodeTemplate
        try:
            node_template = NodeTemplate.objects.get(id=node_id, tenant_id=tenant_id)
            node_template.name = name
            node_template.description = description
            node_template.node_data = node_data
            node_template.fallback_msg = fallback_msg
            node_template.fallback_count = fallback_count
            node_template.category = category
            node_template.save()
        except NodeTemplate.DoesNotExist:
            raise ValidationError(f"No NodeTemplate found with ID {node_id} for tenant {tenant_id}.")
    else:
        # Create a new NodeTemplate
        node_template = NodeTemplate.objects.create(
            name=name,
            description=description,
            node_data=node_data,
            fallback_msg=fallback_msg,
            fallback_count=fallback_count,
            tenant_id=tenant_id,
            category=category
        )
    
    return node_template


@csrf_exempt
def translate_flow(request):
    body = json.loads(request.body)
    languages = body.get('lang')
    id = body.get('id')
    add_translations( languages=languages, node_temp_id=id)

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


OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
client = openai.OpenAI(api_key=OPENAI_API_KEY)


def get_translation(languages, text):
    MODIFIED_PROMPT = f"Text: {text}, Language: {languages}"

    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": "You are an helpful assisstant who is pro at translating Indian Languages. Translate the text provided in english into the languages provided and return only the translated text in Json format for diff languages as language codes."},
            {"role": "user", "content": MODIFIED_PROMPT}
        ]
    )
    result = response.choices[0].message.content
    start = result.find('{')
    end = result.rfind('}')
    result = result[start:end + 1]
    # print("Result: ", result)
    result_json = json.loads(result)

    # print(result_json)

    return result_json

# @shared_task(bind=True, max_retries=3)
def add_translations( languages, node_temp_id):
    try:
        node_template = NodeTemplate.objects.get(id = node_temp_id)
        node_data = node_template.node_data
        nodes = node_data['nodes']
        for node in nodes:
            type = node['type']

            if type == 'sendMessage':
                field_type = node['data']['fields']['type']
                if field_type == "text":
                    text = node['data']['fields']['content']['text']
                    data = get_translation(languages=languages, text=text)

                    translations = {}

                    for lang, value in data.items():
                        translations[f"text_{lang}"] = value

                    # print("Translations: ", translations)

                elif field_type == "Image":
                    text = node['data']['fields']['content']['caption']
                    # print("Caption: ", text)
                    if text:
                        data = get_translation(languages=languages, text=text)
                    
                        translations = {}

                        for lang, value in data.items():
                            translations[f"caption_{lang}"] = value
                        # print("Translations: ", translations)
                
                node['data']['fields']['content'].update(translations)
                # print("Updated Node: ", node)
                # print("Node Type is sendMessage")



            elif type == 'askQuestion':
                options = node['data']['options']
                question = node['data']['question']
                option_translation = {}
                translations = {}

                if len(options) > 0:
                    option_translation = get_translation(languages, options)
                    
                    for lang, values in option_translation.items():
                        translations[f"options_{lang}"] = values

                question_translation = get_translation(languages, question)
                data = {'options': option_translation, 'question': question_translation}


                # Flatten questions
                for lang, value in data["question"].items():
                    translations[f"question_{lang}"] = value

                print("Translations: ", translations)

                node['data'].update(translations)
                print("Updated Node: ", node)
                # print("Node Type is askQuestion")
                
            elif type == 'setCondition':
                condition = node['data']['condition']
                data = get_translation(languages, condition)
                # print("Translations: ", translations)

                translations = {}

                for lang, value in data.items():
                    translations[f"condition_{lang}"] = value

                node['data'].update(translations)
                # print("Node Type is setCondition")

        node_template.save()
        # print("New Node Template: ", node_template.node_data)
    except Exception as e:
        print("Encountered error: ", e)
        return JsonResponse({'success': False, "error": e}, status=500)
            
