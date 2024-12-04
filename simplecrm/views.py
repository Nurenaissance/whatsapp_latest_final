
from django.apps import apps
from django.http import JsonResponse
from rest_framework.decorators import api_view
from .utils import deduplicate_model
from django.db import connection
from rest_framework.response import Response
from rest_framework import status


@api_view(['POST'])
def deduplicate_view(request):
    app_name = request.data.get('app-name')
    model_name = request.data.get('model')
    unique_field = request.data.get('field')
    
    if not app_name or not model_name or not unique_field :
        return JsonResponse({'status': 'error', 'message': 'app-name,model and field name are required.'}, status=400)
    
    try:
        model_class = apps.get_model(app_name, model_name)
    except LookupError:
        return JsonResponse({'status': 'error', 'message': f'Model {model_name} not found in App.'}, status=400)

    try:
        deduplicate_model(model_class, unique_field)
        return JsonResponse({'status': 'success', 'message': f'Duplicates removed successfully from {model_name}.'})
    except Exception as e:
        return JsonResponse({'status': 'error', 'message': str(e)}, status=500)
    
@api_view(['POST'])
def store_selected_emails(request):
    selected_emails = request.data  # Expecting a list of emails

    with connection.cursor() as cursor:
        for email_data in selected_emails:
            email_id = email_data.get('email_id')
            from_address = email_data.get('from')
            subject = email_data.get('subject')
            text = email_data.get('text')

            # Insert email into the selected_emails table
            cursor.execute("""
                INSERT INTO selected_emails (email_id, from_address, subject, text)
                VALUES (%s, %s, %s, %s)
                ON CONFLICT (email_id) DO NOTHING;
            """, [email_id, from_address, subject, text])

    return Response({"message": "Emails stored successfully"}, status=status.HTTP_201_CREATED)


@api_view(['GET'])
def fetch_all_emails(request):
    with connection.cursor() as cursor:
        cursor.execute("SELECT email_id, from_address, subject, text FROM selected_emails;")
        emails = cursor.fetchall()

    # Transform fetched data into a list of dictionaries
    email_list = [
        {
            "email_id": email[0],
            "from_address": email[1],
            "subject": email[2],
            "text": email[3],
        }
        for email in emails
    ]
    
    return Response(email_list, status=status.HTTP_200_OK)
