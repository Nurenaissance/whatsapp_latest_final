# from django.http import JsonResponse
# import pandas as pd
# from django.views.decorators.csrf import csrf_exempt
# import os
# from tablib import Dataset
# from leads import models as leads_models
# from accounts import models as account_models
# from contacts import models as contact_models
# from interaction import models as interaction_models
# from django.contrib.auth.models import User
# user_id = 1
# from django.apps import apps
# import json
# model_mapping = {
#     "Lead": leads_models.Lead,
#     "Account": account_models.Account,
#     "Contact": contact_models.Contact,
#     "Meeting": interaction_models.Meetings,
#     "Call": interaction_models.Calls,
#     # Add more model mappings as needed
# }
# @csrf_exempt
# def ImportLeadData(request):
#     print("Entering ImportLeadData function")
#     if request.method == 'POST' and request.FILES.get('file'):
#         print("POST request received with file")
#         excel_file = request.FILES['file']
#         print("Received file:", excel_file.name)
#         column_mapping_json = request.POST.get('column_mappings_json')
#         if column_mapping_json:
#             column_mapping = json.loads(column_mapping_json)
#             print("Column mapping:", column_mapping)
#         model_name = request.POST.get('model_name')
#         print("Model name:", model_name)
#         try:
#             file_extension = os.path.splitext(excel_file.name)[1].lower()
#             print("File extension:", file_extension)

#             # Specify encoding based on the file extension
#             encoding = 'utf-8' if file_extension in ('.xlsx', '.xls', '.csv') else None
#             print("Encoding:", encoding)

#             if file_extension == '.xlsx':
#                 df = pd.read_excel(excel_file, engine='openpyxl', header=3)
#             elif file_extension == '.xls':
#                 df = pd.read_excel(excel_file, header=3)
#             elif file_extension == '.csv':
#                 df = pd.read_csv(excel_file, header=3)
#             else:
#                 return JsonResponse({'error': 'Unsupported file format'}, status=400)

#             print("Dataframe columns:", df.columns)

#             # Print column names
#             """column_mapping = {
#                 "Market": "first_name",
#                 "Marketing": "last_name",
#                 "Service": "phone",
               
#             }"""

#             # Select only relevant columns from the DataFrame
#             selected_columns = df[list(column_mapping.keys())].copy()
#             print("Selected columns:", selected_columns.columns)

#             # Rename the columns to match the Lead model fields
#             selected_columns.rename(columns=column_mapping, inplace=True)
#             print("Renamed columns:", selected_columns.columns)

#             # Load the selected columns into a Tablib dataset
#             dataset = Dataset().load(selected_columns)

#             print("Dataset:", dataset)

#             # Create instances of Lead model using tablib dataset
#             try:
#                 user = User.objects.get(id=user_id)
#             except User.DoesNotExist:
#                 print(f"User with ID {user_id} does not exist")
#                 user = None

#             # Assign the User instance to the `createdBy` field of the Lead model
#             model = model_mapping.get(model_name)
#             if not model:
#                 return JsonResponse({'error': f'Model {model_name} not found'}, status=400)

#             print("Model:", model)

#             for row in dataset.dict:
#                 print("Processing row:", row)
#                 row['createdBy'] = user
#                 print("User assigned to row:", user)

#                 # Create the Lead instance with the updated row dictionary
#                 model.objects.create(**row)
#                 print("Lead instance created")

#             return JsonResponse({"status": "Lead data imported successfully"})
#         except Exception as e:
#             print("Exception occurred:", e)
#             return JsonResponse({'error': str(e)}, status=500)
#     else:
#         print("No file uploaded")
#         return JsonResponse({'error': 'No file uploaded'}, status=400)
