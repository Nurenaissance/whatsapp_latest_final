from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
from .models import DynamicModel, DynamicField
from .serializers import DynamicModelSerializer
from django.db import models, connection, transaction
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from django.contrib.auth.models import User
from django.conf import settings
from django.contrib.auth import get_user_model
from django.http import JsonResponse
import sys, json
from django.core.exceptions import ObjectDoesNotExist
import re
from tenant.models import Tenant


User =  get_user_model()

def get_dynamic_model_class(model_name):
    """Get the dynamic model class."""
    try:
        # Meta class definition
        class Meta:
            app_label = 'dynamic_entities'

        # Create attributes dictionary for the dynamic model
        attrs = {'__module__': 'dynamic_entities.models', 'Meta': Meta}

        # Fetch dynamic fields for the given model name
        fields = DynamicField.objects.filter(dynamic_model__model_name=model_name)
        print("fields: ", fields)

        # Loop through each field and assign the appropriate Django model field type
        for field in fields:
            field_type = field.field_type

            if field_type == 'string':
                attrs[field.field_name] = models.CharField(max_length=255)
            elif field_type == 'integer':
                attrs[field.field_name] = models.IntegerField()
            elif field_type == 'text':
                attrs[field.field_name] = models.TextField()
            elif field_type == 'boolean':
                attrs[field.field_name] = models.BooleanField()
            elif field_type == 'date':
                attrs[field.field_name] = models.DateField()
            elif field_type == 'bigint':
                attrs[field.field_name] = models.BigIntegerField()
            else:
                raise ValueError(f'Unknown field type: {field_type}')
        
        # Return the dynamically created model class
        return type(model_name, (models.Model,), attrs)

    except DynamicField.DoesNotExist:
        print(f"No dynamic fields found for the model: {model_name}")
    except ValueError as e:
        print(f"Error: {e}")
    except Exception as e:
        print(f"An unexpected error occurred at get dynamic model class: {e}")

def deregister_dynamic_model(model_name):
    """Deregister the dynamic model class."""
    model_module = sys.modules.get('dynamic_entities.models')
    if model_module:
        lowercase_model_name = model_name.lower()
        capitalized_model_name = model_name.capitalize()
        if hasattr(model_module, lowercase_model_name):
            delattr(model_module, lowercase_model_name)
        if hasattr(model_module, capitalized_model_name):
            delattr(model_module, capitalized_model_name)

def create_dynamic_model(model_name, fields, tenant_id, user=None):
    try:
        try:
            tenant = Tenant.objects.get(id=tenant_id)
        except Tenant.DoesNotExist:
            return {'success': False, 'message': f'Tenant with id {tenant_id} does not exist'}
        except Exception as e:
            return {'success': False, 'message': f'Error retrieving tenant: {str(e)}'}

        try:
            default_user = user if user else User.objects.first()
            if not default_user:
                raise ValidationError('No default user found')
        except ValidationError as e:
            return {'success': False, 'message': str(e)}
        except Exception as e:
            return {'success': False, 'message': f'Error retrieving default user: {str(e)}'}

        field_definitions = {
            '__module__': 'dynamic_entities.models',
            'Meta': type('Meta', (), {'app_label': 'dynamic_entities'})
        }

        for field in fields:
            field_name = field.get('field_name')
            field_type = field.get('field_type', 'string')

            if not field_name:
                return {'success': False, 'message': 'Field name is required'}

            if field_type == 'string':
                field_definitions[field_name] = models.CharField(max_length=255, null=True, blank=True)
            elif field_type == 'integer':
                field_definitions[field_name] = models.IntegerField(null=True, blank=True)
            elif field_type == 'text':
                field_definitions[field_name] = models.TextField(null=True, blank=True)
            elif field_type == 'boolean':
                field_definitions[field_name] = models.BooleanField(null=True, blank=True)
            elif field_type == 'date':
                field_definitions[field_name] = models.DateField(null=True, blank=True)
            elif field_type == 'bigint':
                field_definitions[field_name] = models.BigIntegerField(null=True, blank=True)
            else:
                return {'success': False, 'message': f'Unknown field type: {field_type}'}

        try:
            model_class = type(model_name, (models.Model,), field_definitions)
            print(f"Model class created: {model_class}")
        except Exception as e:
            return {'success': False, 'message': f'Error creating model class: {str(e)}'}

        try:
            with connection.schema_editor() as schema_editor:
                schema_editor.create_model(model_class)
        except Exception as e:
            return {'success': False, 'message': f'Error creating model schema: {str(e)}'}

        try:
            with transaction.atomic():
                dynamic_model = DynamicModel.objects.create(model_name=model_name, created_by=default_user, tenant=tenant)

                for field in fields:
                    DynamicField.objects.create(
                        dynamic_model=dynamic_model,
                        field_name=field['field_name'],
                        field_type=field['field_type']
                    )

                table_name = f"dynamic_entities_{model_name.lower()}"
                with connection.cursor() as cursor:
                    cursor.execute(f'ALTER TABLE "{table_name}" OWNER TO crm_tenant')
                    cursor.execute(f'GRANT ALL PRIVILEGES ON TABLE "{table_name}" TO crm_tenant')
                    cursor.execute(f'GRANT SELECT, INSERT, UPDATE, DELETE ON TABLE "{table_name}" TO public')

        except Exception as e:
            print(f"Error during dynamic model creation: {str(e)}")
            return {'success': False, 'message': f'Error during dynamic model creation: {str(e)}'}

        print(f"Dynamic model created successfully: {model_name}")
        return {'success': True, 'message': f'Dynamic model "{model_name}" created successfully'}

    except Exception as e:
        print(f"Unexpected error occurred: {str(e)}")
        return {'success': False, 'message': f'Unexpected error occurred: {str(e)}'}  

@method_decorator(csrf_exempt, name='dispatch')
class CreateDynamicModelView(APIView):
    
    def post(self, request, *args, **kwargs):
        serializer = DynamicModelSerializer(data=request.data)
        if serializer.is_valid():
            validated_data = serializer.validated_data
            model_name = validated_data.get('model_name')
            fields = validated_data.get('fields')
            tenant_id = request.headers.get('X-Tenant-Id')

            user = request.user if request.user.is_authenticated else None
            result = create_dynamic_model(model_name, fields, user, tenant_id)

            if result['success']:
                return Response(result, status=status.HTTP_201_CREATED)
            else:
                return Response(result, status=status.HTTP_400_BAD_REQUEST)
        else:
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    
class DynamicModelListView(APIView):
    @staticmethod
    def sanitize_model_name(model_name):
        """Sanitize model name to ensure it's a valid SQL identifier."""
        return re.sub(r'\W|^(?=\d)', '_', model_name.lower())

    def get(self, request, *args, **kwargs):
        dynamic_models = DynamicModel.objects.all()
        response_data = []

        for dynamic_model in dynamic_models:
            try:
                sanitized_model_name = self.sanitize_model_name(dynamic_model.model_name)
                table_name = f"dynamic_entities_{sanitized_model_name}"

                # Check if the table exists
                with connection.cursor() as cursor:
                    cursor.execute("SELECT to_regclass(%s)", [table_name])
                    if cursor.fetchone()[0] is None:
                        raise ValueError(f"Table for model {dynamic_model.model_name} does not exist.")

                # Retrieve associated fields
                fields = DynamicField.objects.filter(dynamic_model=dynamic_model)
                fields_data = [{'field_name': field.field_name, 'field_type': field.field_type} for field in fields]

                # Safely retrieve the created_by username or handle missing user
                try:
                    created_by_username = dynamic_model.created_by.username
                except ObjectDoesNotExist:
                    created_by_username = 'Unknown User'

                # Prepare model data for response
                model_data = {
                    'model_name': dynamic_model.model_name,
                    'created_by': created_by_username,
                    'fields': fields_data
                }
                response_data.append(model_data)

            except ValueError:
                # Log deletion for future audit or monitoring
                # print(f"Deleting model: {dynamic_model.model_name} due to missing table.")
                dynamic_model.delete()

        return Response(response_data, status=status.HTTP_200_OK)


from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from django.core.exceptions import ObjectDoesNotExist, ValidationError

class DynamicModelDataView(APIView):
    def get(self, request, model_name, *args, **kwargs):
        try:
            model_class = get_dynamic_model_class(model_name)
            data = model_class.objects.all().values()
            return Response(list(data), status=status.HTTP_200_OK)
        except ObjectDoesNotExist as e:
            print(f"Error: Model not found - {e}")
            return Response({'success': False, 'message': 'Model not found'}, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            print(f"General Exception in GET: {e}")
            return Response({'success': False, 'message': str(e)}, status=status.HTTP_400_BAD_REQUEST)

    def post(self, request, model_name, *args, **kwargs):
        try:
            print("model name and type: ", model_name, type(model_name))
            model_class = get_dynamic_model_class(model_name)
            print()
            fields = [f.name for f in model_class._meta.get_fields()]
            print(f"Available fields in {model_name}: {fields}")  # Debugging the fields

            data = request.data
            phone_no = data.get('phone_no', None)
            if phone_no:
                phone_no = int(phone_no)
                print(type(phone_no))
              
            if 'phone_no' not in fields:
                return Response({'success': False, 'message': 'phone_no field does not exist in the model'}, status=status.HTTP_400_BAD_REQUEST)
            
            if not phone_no:
                return Response({'success': False, 'message': 'phone_no is required'}, status=status.HTTP_400_BAD_REQUEST)
            
            # Check if the instance with the given phone_no exists
            instance = model_class.objects.filter(phone_no=phone_no).first()
            if instance:
                for attr, value in data.items():
                    setattr(instance, attr, value)
                instance.save()
                message = 'Data updated successfully'
                status_code = status.HTTP_200_OK
            else:
                instance = model_class.objects.create(**data)
                message = 'Data added successfully'
                status_code = status.HTTP_201_CREATED

            return Response({'success': True, 'message': message, 'data': instance.id}, status=status_code)
        except ValidationError as e:
            return Response({'success': False, 'message': str(e)}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            print(f"General Exception in POST: {e}")
            return Response({'success': False, 'message': str(e)}, status=status.HTTP_400_BAD_REQUEST)

    def put(self, request, model_name, *args, **kwargs):
        phone_no = request.data.get('phone_no', None)
        if not phone_no:
            return Response({'success': False, 'message': 'phone_no is required for updating data'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            model_class = get_dynamic_model_class(model_name)
            data = request.data
            data.pop('phone_no')
            instance = model_class.objects.filter(phone_no=phone_no).first()
            if not instance:
                return Response({'success': False, 'message': 'Instance not found for the given phone_no'}, status=status.HTTP_404_NOT_FOUND)

            for attr, value in data.items():
                setattr(instance, attr, value)
            instance.save()

            return Response({'success': True, 'message': 'Data updated successfully'}, status=status.HTTP_200_OK)
        except ValidationError as e:
            print(f"Validation Error in PUT: {e}")
            return Response({'success': False, 'message': str(e)}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            print(f"General Exception in PUT: {e}")
            return Response({'success': False, 'message': str(e)}, status=status.HTTP_400_BAD_REQUEST)
     

class DeleteDynamicModelView(APIView):
    def delete(self, request, model_name, *args, **kwargs):
        try:
            model_class = get_dynamic_model_class(model_name)
            with connection.schema_editor() as schema_editor:
                schema_editor.delete_model(model_class)

            deregister_dynamic_model(model_name)
            DynamicModel.objects.filter(model_name=model_name).delete()
            DynamicField.objects.filter(dynamic_model__model_name=model_name).delete()
            return Response({'success': True, 'message': f'Model {model_name} deleted successfully'}, status=status.HTTP_200_OK)
        except Exception as e:
            return Response({'success': False, 'message': str(e)}, status=status.HTTP_400_BAD_REQUEST)
        
@csrf_exempt
def addDynamicModelData(request):
    if request.method != 'POST':
        return JsonResponse({'message': 'Only POST requests are allowed'}, status=405)

    try:
        req_body = request.body
        data = json.loads(req_body)

        required_keys = {'flow_name', 'input_variable', 'value', 'phone'}
        if not required_keys.issubset(data):
            return JsonResponse({'error': 'Missing required parameters'}, status=400)

        flow_name = data['flow_name']
        variable = data['input_variable']
        sanitized_variable = f'"{variable}"'  # Wrap the variable in quotes to handle special characters

        value = data['value']
        phone = data['phone']
        tenant = request.headers.get('X-Tenant-Id')
        table_name = f"models_{tenant}_{flow_name}"

        query = f"""
            INSERT INTO {table_name} (phone_no, {sanitized_variable})
            VALUES (%s, %s)
            ON CONFLICT (phone_no)
            DO UPDATE SET {sanitized_variable} = EXCLUDED.{sanitized_variable};
        """

        with connection.cursor() as cursor:
            cursor.execute(query, [phone, value])

        return JsonResponse({'message': 'Success'}, status=200)

    except json.JSONDecodeError:
        return JsonResponse({'error': 'Invalid JSON format'}, status=400)

    except KeyError as e:
        return JsonResponse({'error': f'Missing key: {str(e)}'}, status=400)

    except Exception as e:
        return JsonResponse({'error': f'Unexpected error: {str(e)}'}, status=500)
    
from django.db import connection, transaction
from django.db.utils import IntegrityError

def createDynamicModel(model_name, fields, tenant_id):
    try:
        table_name = f"models_{tenant_id}_{model_name}"
        with connection.cursor() as cursor:
            cursor.execute(f"""
                SELECT EXISTS (
                    SELECT FROM information_schema.tables
                    WHERE table_name = %s
                );
            """, [table_name])
            exists = cursor.fetchone()[0]
        
        if exists:
            with connection.cursor() as cursor:
                cursor.execute(f"""
                    SELECT column_name FROM information_schema.columns
                    WHERE table_name = %s;
                """, [table_name])
                existing_columns = {row[0] for row in cursor.fetchall()}
            
            new_columns = []
            
            for field in fields:
                field_name = field.get('field_name')
                field_type = field.get('field_type').lower()
                
                if field_name in existing_columns:
                    continue
                
                if field_type == 'string':
                    sql_type = 'VARCHAR(255)'
                elif field_type == 'integer':
                    sql_type = 'INTEGER'
                elif field_type == 'text':
                    sql_type = 'TEXT'
                elif field_type == 'boolean':
                    sql_type = 'BOOLEAN'
                elif field_type == 'date':
                    sql_type = 'DATE'
                elif field_type == 'bigint':
                    sql_type = 'BIGINT'
                else:
                    raise ValueError(f"Invalid field type: {field_type}")
                
                new_columns.append(f'ADD COLUMN "{field_name}" {sql_type}')
            
            if new_columns:
                alter_table_query = f"""
                    ALTER TABLE "{table_name}" {', '.join(new_columns)};
                """
                
                with connection.cursor() as cursor:
                    with transaction.atomic():
                        try:
                            cursor.execute(alter_table_query)
                            print(f"Updated table '{table_name}' with new columns.")
                            return {'success': True, 'message': f'Table "{table_name}" updated with new fields.'}
                        except IntegrityError as e:
                            print(f"Error updating table: {e}")
                            raise e
            
            return {'success': True, 'message': f'Table "{table_name}" already exists. No new fields added.'}

        columns = []
        primary_key = "id BIGSERIAL PRIMARY KEY"  # Default primary key
        
        for field in fields:
            field_name = field.get('field_name')
            field_type = field.get('field_type').lower()
            
            if not field_name or not isinstance(field_name, str) or len(field_name) == 0:
                raise ValueError(f"Invalid field name: {field_name}")
            
            if not field_type or field_type not in ['string', 'integer', 'text', 'boolean', 'date', 'bigint']:
                raise ValueError(f"Invalid field type: {field_type}")

            if field_name == 'phone_no':
                primary_key = '"phone_no" BIGINT PRIMARY KEY'
                continue  # Skip adding it as a regular column

            if field_type == 'string':
                sql_type = 'VARCHAR(255)'
            elif field_type == 'integer':
                sql_type = 'INTEGER'
            elif field_type == 'text':
                sql_type = 'TEXT'
            elif field_type == 'boolean':
                sql_type = 'BOOLEAN'
            elif field_type == 'date':
                sql_type = 'DATE'
            elif field_type == 'bigint':
                sql_type = 'BIGINT'
            
            columns.append(f'"{field_name}" {sql_type}')
        
        create_table_query = f"""
            CREATE TABLE "{table_name}" (
                {primary_key},
                {', '.join(columns)}
            );
        """

        with connection.cursor() as cursor:
            with transaction.atomic():
                try:
                    cursor.execute(create_table_query)
                    print(f"Table '{table_name}' created successfully.")
                    
                    cursor.execute(f'GRANT ALL PRIVILEGES ON TABLE "{table_name}" TO crm_tenant')
                    cursor.execute(f'GRANT SELECT, INSERT, UPDATE, DELETE ON TABLE "{table_name}" TO public')
                    
                    tenant = Tenant.objects.get(id=tenant_id)
                    default_user = User.objects.first()
                    DynamicModel.objects.create(model_name=model_name, created_by=default_user, tenant=tenant)

                    return {'success': True, 'message': f'Table "{table_name}" created successfully.'}
                
                except IntegrityError as e:
                    print(f"Error creating table: {e}")
                    raise e
        
    except ValueError as e:
        print(f"Input validation error: {e}")
        return {'success': False, 'message': str(e)}
    except Exception as e:
        print(f"Error during table creation: {str(e)}")
        return {'success': False, 'message': f"Error during table creation: {str(e)}"}

def getDynamicModelData(request, model_name):
    tenant_id = request.headers.get('X-Tenant-Id')

    if not tenant_id:
        return JsonResponse({'success': False, 'message': 'Tenant ID is required'}, status=400)

    table_name = f"models_{tenant_id}_{model_name}"

    try:
        with connection.cursor() as cursor:
            # Check if table exists
            cursor.execute("""
                SELECT EXISTS (
                    SELECT FROM information_schema.tables
                    WHERE table_name = %s
                );
            """, [table_name])
            exists = cursor.fetchone()[0]

            if not exists:
                return JsonResponse({'success': False, 'message': f'Table "{table_name}" does not exist'}, status=404)

            # Fetch all data from the table
            cursor.execute(f'SELECT * FROM "{table_name}";')
            columns = [col[0] for col in cursor.description]  # Get column names
            rows = cursor.fetchall()  # Fetch data

            data = [dict(zip(columns, row)) for row in rows]  # Convert rows to dicts

        return JsonResponse(data, safe=False, status=200)  # Return as list

    except Exception as e:
        return JsonResponse({'success': False, 'message': str(e)}, status=500)


# curl --location 'https://testexpenses.drishtee.in/rrp/nuren/checkRRP' \
# --header 'Content-Type: application/json' \
# --data '{
#            "rrp_phone_no": "8720962751"
# }'