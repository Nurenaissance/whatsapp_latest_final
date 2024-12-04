from django.http import JsonResponse
import pandas as pd
import os, json,requests
from openai import OpenAI
from contacts import models as contact_models
from interaction import models as interaction_models
from django.views.decorators.csrf import csrf_exempt


model_mapping = {
    "Contact": contact_models.Contact,
    
}


@csrf_exempt
def get_excel_columns(request):
    if request.method == 'POST' and request.FILES.get('file'):
        excel_file = request.FILES['file']
        num = int(request.POST.get('startrow'))
        try:
            file_extension = os.path.splitext(excel_file.name)[1].lower()
            encoding = 'latin1' if file_extension in ('.xlsx', '.xls', '.csv') else None

            if file_extension == '.xlsx':
                df = pd.read_excel(excel_file, engine='openpyxl', header=num)
            elif file_extension == '.xls':
                df = pd.read_excel(excel_file, header=num)
            elif file_extension == '.csv':
                df = pd.read_csv(excel_file, header=num)
            else:
                return JsonResponse({'error': 'Unsupported file format'}, status=400)

            column_names = df.columns.tolist()

            return JsonResponse({"columns": column_names})
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=500)
    else:
        return JsonResponse({'error': 'No file uploaded'}, status=400)


def get_model_fields(model_name):
    model = model_mapping.get(model_name)
    if not model:
        return JsonResponse({'error': f'Model {model_name} not found'}, status=400)

    return [field.name for field in model._meta.get_fields()]


def get_column_mappings(list1, list2):
    print("rcvd list1: " ,list1)
    print("rcvd list2: ", list2)
    client = OpenAI(api_key = os.getenv("OPENAI_API_KEY"))
    response = client.chat.completions.create(
        model = "gpt-4o-mini",
        messages = [
            {
                "role": "system",
                "content": "You are an expert software that helps to map two given lists and return answer in only json format."
            },
            {
                "role": "user",
                "content": f"map these two lists one to one: list1={list1} and list2={list2} return ONLY the answer in json format with null values with unmapped ones"
            }
        ]
    )
    result = response.choices[0].message.content
        
        #trim the result
    fin=result.find('{')
    lin=result.rfind('}')
    trimmed_result = result [fin:lin + 1]

    parsed_result = json.loads(trimmed_result)

    return parsed_result
    