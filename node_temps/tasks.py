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

    print(result_json)

    return result_json

@shared_task(bind=True, max_retries=3)
def add_translations(self, languages, node_temp_id):
    node_template = NodeTemplate.objects.get(id = node_temp_id)
    node_data = node_template.node_data
    nodes = node_data['nodes']
    for node in nodes:
        type = node['type']

        if type == 'sendMessage':
            field_type = node['data']['fields']['type']
            if field_type == "text":
                text = node['data']['fields']['content']['text']
                translations = get_translation(languages=languages, text=text)
                print("Translations: ", translations)
            elif field_type == "image":
                text = node['data']['fields']['content']['caption']
                translations = get_translation(languages=languages, text=text)
                print("Translations: ", translations)

        elif type == 'askQuestion':
            print("Node Type is askQuestion")
        elif type == 'setCondition':
            print("Node Type is setCondition")
            
