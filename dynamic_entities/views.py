from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
from .models import DynamicModel, DynamicField
from .serializers import DynamicModelSerializer
from django.db import models, connection
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from django.contrib.auth.models import User
from django.conf import settings
from django.contrib.auth import get_user_model
import sys
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

def create_dynamic_model(model_name, fields,tenant_id ,user=None):
    try:
        # Define model fields
        field_definitions = {
            '__module__': 'dynamic_entities.models',
            'Meta': type('Meta', (), {'app_label': 'dynamic_entities'})
        }
        print("Field definitions: ", field_definitions)
        
        try:
            for field in fields:
                field_name = field['field_name']
                field_type = field.get('field_type') or 'string'
                print(field_name, field_type)
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
                    raise ValueError(f'Unknown field type: {field_type}')
        except KeyError as e:
            print("keyerror: ", e)
            return {'success': False, 'message': f'Missing field in input data: {str(e)}'}
        except ValueError as e:
            print("value error: ", e)
            return {'success': False, 'message': str(e)}
        
        # Create model class
        try:
            model_class = type(model_name, (models.Model,), field_definitions)
            print("Model class: ", model_class)
        except Exception as e:
            print("exceptions: ", e)
            return {'success': False, 'message': f'Error creating model class: {str(e)}'}

        # Create model schema
        try:
            with connection.schema_editor() as schema_editor:
                schema_editor.create_model(model_class)
        except Exception as e:
            print("exceptions in model schemma: ", e)
            return {'success': False, 'message': f'Error creating model schema: {str(e)}'}
        
        try: 
            tenant = Tenant.objects.filter(id = tenant_id)
        except Exception as e:
            return {'success': False, 'message': f'Error retrieving tenant from tenant_id : {str(e)}'}
        # Get default user
        try:
            default_user = user if user else User.objects.first()
            if not default_user:
                raise ValidationError('No default user found')
        except ValidationError as e:
            return {'success': False, 'message': str(e)}
        except Exception as e:
            return {'success': False, 'message': f'Error retrieving default user: {str(e)}'}

        # Create dynamic model record
        try:
            dynamic_model = DynamicModel.objects.create(model_name=model_name, created_by=default_user)
        except Exception as e:
            print("error creating dynmicn:", e)
            return {'success': False, 'message': f'Error creating DynamicModel record: {str(e)}'}

        # Create dynamic fields
        try:
            for field in fields:
                DynamicField.objects.create(dynamic_model=dynamic_model, field_name=field['field_name'], field_type=field['field_type'])
        except Exception as e:
            print("erororrororor: ", e)
            return {'success': False, 'message': f'Error creating DynamicField records: {str(e)}'}

        # Set table permissions
        try:
            table_name = f"dynamic_entities_{model_name.lower()}"
            with connection.cursor() as cursor:
                cursor.execute(f'ALTER TABLE "{table_name}" OWNER TO crm_tenant')
                cursor.execute(f'GRANT ALL PRIVILEGES ON TABLE "{table_name}" TO crm_tenant')
                cursor.execute(f'GRANT SELECT, INSERT, UPDATE, DELETE ON TABLE "{table_name}" TO public')
        except Exception as e:
            print("error: ", e)
            return {'success': False, 'message': f'Error setting table permissions: {str(e)}'}

        print(f"Dynamic Field Created with model name: {model_name} and fields: {fields}")
        return {'success': True, 'message': f'Dynamic model "{model_name}" created successfully'}
    
    except Exception as e:
        print("ERROR OCCURRED while creating dynamic field: ", str(e))
        return {'success': False, 'message': str(e)}
    

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