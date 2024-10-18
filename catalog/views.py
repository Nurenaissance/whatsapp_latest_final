from django.shortcuts import render
from .models import Catalog
from .seriliazers import CatalogSerializer
from rest_framework import generics, exceptions, response, status
from tenant.models import Tenant
from django.views.decorators.csrf import csrf_exempt
import json
from django.http import JsonResponse


class CatalogListCreateAPIView(generics.ListCreateAPIView):
    queryset = Catalog.objects.all()
    serializer_class = CatalogSerializer

    def get_queryset(self):
        tenant_id = self.request.headers.get('X-Tenant-Id')
        print(f"Tenant ID from headers: {tenant_id}")
        return Catalog.objects.filter(tenant_id=tenant_id)

    def create(self, request, *args, **kwargs):
        tenant_id = self.request.headers.get('X-Tenant-Id')
        print(f"Tenant ID from headers in create: {tenant_id}")

        try:
            tenant = Tenant.objects.get(id=tenant_id)
            print(f"Tenant found: {tenant}")
        except Tenant.DoesNotExist:
            print("Tenant not found")
            raise exceptions.NotFound("Tenant not found.")

        data = request.data
        print(f"Data received: {data}")
        
        # Check if the data is a list or a single dictionary
        if isinstance(data, list):
            print("Data is a list")
            for index, item in enumerate(data):
                item['tenant'] = tenant.id
                print(f"Tenant ID added to item {index}: {item}")
            many = True
        else:
            print("Data is a single dictionary")
            data['tenant'] = tenant.id
            print(f"Tenant ID added to data: {data}")
            many = False

        # Initialize serializer
        serializer = self.get_serializer(data=data, many=many)
        print("Serializer initialized")

        try:
            serializer.is_valid(raise_exception=True)
            print("Serializer is valid")
        except Exception as e:
            print(f"Serializer validation error: {e}")
            return response.Response({"error": "Serializer validation failed", "details": serializer.errors}, status=status.HTTP_400_BAD_REQUEST)


        # Save data
        self.perform_create(serializer)
        print("Data saved successfully")

        headers = self.get_success_headers(serializer.data)
        return response.Response(serializer.data, status=status.HTTP_201_CREATED, headers=headers)


@csrf_exempt
def process_order(request):
    try:
        data = json.loads(request.body)
        print("data: ", data)
        
        order = data.get('order', [])
        
        if not order:
            return JsonResponse({'error': 'No order data found'}, status=400)
        
        insufficient_quantity_errors = []
        querysets = []
        for product in order:
            try:
                product_id = product.get('id')
                quantity = product.get('quantity')
                
                if product_id is None or quantity is None:
                    return JsonResponse({'error': 'Product id or quantity is missing'}, status=400)
                
                queryset = Catalog.objects.get(product_retailer_id=product_id)
                
                if queryset.quantity < quantity:
                    insufficient_quantity_errors.append({
                        'product_id': product_id,
                        'requested_quantity': quantity,
                        'available_quantity': queryset.quantity
                    })
                else:
                    queryset.quantity -= quantity
                    querysets.append(queryset)

            except Catalog.DoesNotExist:
                return JsonResponse({'error': f'Product with id {product_id} not found'}, status=404)
            except ValueError:
                return JsonResponse({'error': 'Invalid quantity value'}, status=400)


        if insufficient_quantity_errors:
            return JsonResponse({
                'status': 'failure',
                'reason': 'insufficient_quantity',
                'insufficient_quantities': insufficient_quantity_errors
            }, status=200)
        
        else: 
            for queryset in querysets:
                queryset.save()

        return JsonResponse({'status': 'success', 'message': 'Order processed successfully'}, status=200)

    except json.JSONDecodeError:
        return JsonResponse({'error': 'Invalid JSON'}, status=400)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)