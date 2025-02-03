from django.shortcuts import render
from datetime import datetime
from django.utils import timezone
import requests, base64, json, os, pytz
from django.views.decorators.csrf import csrf_exempt
from django.http import JsonResponse
from .models import Plan, Subscription

def unix_to_datetime(unix_timestamp):
    """
    Convert a Unix timestamp to a Django-compatible timezone-aware DateTimeField.
    
    Args:
        unix_timestamp (int or None): The Unix timestamp in seconds.
    
    Returns:
        datetime or None: A timezone-aware datetime object or None if input is invalid.
    """
    if unix_timestamp is None:
        return None 
    
    india_tz = pytz.timezone('Asia/Kolkata')  # Define India Standard Time (IST)

    dt = datetime.fromtimestamp(unix_timestamp, india_tz)
    print("returning dt: ", dt)
    return dt


@csrf_exempt
def createSubscription(request):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            tenant_id = request.headers.get('X-Tenant-Id')
            plan_id = data.get('plan_id')

            subscription = create_razorpay_subscription(plan_id, 6, 1, customer_notify=1)

            
            print("Subscription created: ", subscription)

            Subscription2.objects.create(
                id=subscription['id'],
                tenant = tenant_id,
                past_payments = [],
                payment_url = subscription['short_url']
            )

            return JsonResponse(subscription, status=200)
        
        except json.JSONDecodeError:
            return JsonResponse({'error': 'Invalid JSON data'}, status=400)
        except requests.exceptions.RequestException as e:
            return JsonResponse({'error': str(e)}, status=500)
        except Exception as e:
            return JsonResponse({'error': f'An unexpected error occurred - {e}'}, status=500)
    
    else:
        return JsonResponse({'error': 'Only POST requests are allowed'}, status=405)
    
# @csrf_exempt
# def createSubscription(request):
#     if request.method == 'POST':
#         try:
#             data = json.loads(request.body)
#             tenant_id = request.headers.get('X-Tenant-Id')
#             plan_id = data.get('plan_id')
#             period = data.get('period')
#             total_count = data.get('total_count', 1)
#             quantity = data.get('quantity', 1)
#             customer_notify = data.get('customer_notify') #0 for business, 1 for razorpay
#             start_at = data.get('start_at')

#             if period == "weekly":
#                 expire_by = start_at + 7*24*60*60*quantity
#             elif period == "monthly":
#                 expire_by = start_at + 30*24*60*60*quantity
#             elif period == "yearly":
#                 expire_by = start_at + 365*24*60*60*quantity
#             elif period == "daily":
#                 expire_by = start_at + 24*60*60*quantity

#             # addons = data.get('addons')
#             # offer_id = data.get('offer_id')
#             # notes = data.get('notes')
            
#             # if not all([plan_id, total_count, quantity, customer_notify, start_at, expire_by]):
#             #     print(plan_id, total_count, quantity, customer_notify, start_at, expire_by)
#             #     return JsonResponse({'error': 'Missing required fields'}, status=400)
            
#             subscription = create_razorpay_subscription( plan_id, total_count, quantity, customer_notify, start_at, expire_by)

#             print("Subscription created: ", subscription)

#             Subscription.objects.update_or_create(
#                 id=subscription['id'],
#                 defaults={
#                     'plan_id': subscription.get('plan_id', ''),
#                     'plan_name': Plan.objects.filter(id=plan_id).values_list("name", flat=True).first(),  # Replace with logic to fetch plan name if necessary
#                     'status': subscription.get('status', 'created'),
#                     'current_start': unix_to_datetime(subscription.get('current_start')),
#                     'current_end': unix_to_datetime(subscription.get('current_end')),
#                     'ended_at': unix_to_datetime(subscription.get('ended_at')),
#                     'notes': subscription.get('notes', []),
#                     'charge_at': unix_to_datetime(subscription.get('charge_at')),
#                     'start_at': unix_to_datetime(subscription.get('start_at')),
#                     'end_at': unix_to_datetime(subscription.get('end_at')),
#                     'total_count': subscription.get('total_count', 1),
#                     'paid_count': subscription.get('paid_count', 0),
#                     'remaining_count': subscription.get('remaining_count', 0),
#                     'customer_notify': subscription.get('customer_notify', True),
#                     'created_at': subscription.get('created_at', 0),
#                     'expire_by': unix_to_datetime(subscription.get('expire_by')),
#                     'short_url': subscription.get('short_url', ''),
#                     'has_scheduled_changes': subscription.get('has_scheduled_changes', False),
#                     'change_scheduled_at': unix_to_datetime(subscription.get('change_scheduled_at')),
#                     'source': subscription.get('source', 'api'),
#                     'offer_id': subscription.get('offer_id', None),
#                     'tenant': tenant_id
#                 }
#             )

#             return JsonResponse(subscription, status=200)
        
#         except json.JSONDecodeError:
#             return JsonResponse({'error': 'Invalid JSON data'}, status=400)
#         except requests.exceptions.RequestException as e:
#             return JsonResponse({'error': str(e)}, status=500)
#         except Exception as e:
#             return JsonResponse({'error': f'An unexpected error occurred - {e}'}, status=500)
    
#     else:
#         return JsonResponse({'error': 'Only POST requests are allowed'}, status=405)

API_KEY_ID = os.getenv("RAZORPAY_API_KEY")
API_KEY_SECRET = os.getenv('RAZORPAY_API_SECRET')

import base64
import requests

def create_razorpay_subscription(plan_id, total_count, quantity, customer_notify):
    try:
        url = "https://api.razorpay.com/v1/subscriptions"
        
        headers = {
            "Content-Type": "application/json",
        }
        
        payload = {
            "plan_id": plan_id,
            "total_count": total_count,
            "quantity": quantity,
            "customer_notify": customer_notify
        }
        print("trying:   ", payload)
        response = requests.post(url, auth=(API_KEY_ID, API_KEY_SECRET), headers=headers, json=payload)
        print(response.json())
        # Check if the response was successful
        if response.status_code == 200:
            return response.json()  # Return the response JSON if successful
        else:
            # Raise exception if status code is not 200 (OK)
            response.raise_for_status()
    
    except requests.exceptions.RequestException as e:
        # Catch any issues with the HTTP request (network, timeout, invalid response, etc.)
        print(f"Request error: {str(e)}")
        return {'error': f"Request error: {str(e)}"}
    
    except requests.exceptions.HTTPError as e:
        # Catch HTTP errors with status codes like 400, 500, etc.
        print(f"HTTP error: {str(e)}")
        return {'error': f"HTTP error: {str(e)}"}
    
    except Exception as e:
        # Catch any other unexpected errors
        print(f"Unexpected error: {str(e)}")
        return {'error': f"Unexpected error: {str(e)}"}
    

def fetch_plans():
    """
    Fetches plans from Razorpay API and stores them in the database.
    """
    url = "https://api.razorpay.com/v1/plans"
    
    
    response = requests.get(url, auth=(API_KEY_ID, API_KEY_SECRET))

    if response.status_code == 200:
        data = response.json()
        plans = data.get("items", [])

        for plan in plans:
            created_at = unix_to_datetime(plan["item"]["created_at"])
            Plan.objects.update_or_create(
                id=plan["id"],
                defaults={
                    "period": plan["period"],
                    "interval": plan["interval"],
                    "active": plan["item"]["active"],
                    "name": plan["item"]["name"],
                    "description": plan["item"].get("description", ""),
                    "amount": plan["item"]["amount"]/100,
                    "currency": plan["item"]["currency"],
                    "created_at": created_at
                }
            )
        
        return f"Successfully stored {len(plans)} plans!"
    
    else:
        return f"Error {response.status_code}: {response.text}"

def fetch_subscriptions():
    """Fetch subscriptions from Razorpay API and store/update them in the database."""
    url = 'https://api.razorpay.com/v1/subscriptions'

    try:
        response = requests.get(url, auth=(API_KEY_ID, API_KEY_SECRET))
        response.raise_for_status()  # Raise an exception for HTTP errors (4xx, 5xx)

        data = response.json()
        subscriptions = data.get("items", [])

        for subscription in subscriptions:
            plan_id = subscription.get("plan_id")
            
            # status = subscription["status"]

            # if status == "expired":
            #     subscription_id = subscription["id"]
            #     try:
            #         subscription = Subscription.objects.get(id=subscription_id)
            #     except Subscription.DoesNotExist:
            #         # raise NotFound(detail="Subscription not found", code=404)
            #         print(f"Subscription {subscription_id} not found")
            #         continue
                
            #     subscription.delete()


            plan_name = Plan.objects.filter(id=plan_id).values_list("name", flat=True).first() or "Unknown Plan"

            Subscription.objects.update_or_create(
                id=subscription["id"],
                defaults={
                    "plan_id": plan_id,
                    "plan_name": plan_name,
                    "status": subscription.get("status", "created"),

                    # Convert timestamps
                    "current_start": unix_to_datetime(subscription.get("current_start")),
                    "current_end": unix_to_datetime(subscription.get("current_end")),
                    "ended_at": unix_to_datetime(subscription.get("ended_at")),
                    "charge_at": unix_to_datetime(subscription.get("charge_at")),
                    "start_at": unix_to_datetime(subscription.get("start_at")),
                    "end_at": unix_to_datetime(subscription.get("end_at")),
                    "change_scheduled_at": unix_to_datetime(subscription.get("change_scheduled_at")),

                    # Other fields
                    "total_count": subscription.get("total_count", 1),
                    "paid_count": subscription.get("paid_count", 0),
                    "remaining_count": subscription.get("remaining_count", 0),
                    "customer_notify": subscription.get("customer_notify", False),
                    "created_at": subscription.get("created_at", 0),
                    "expire_by": subscription.get("expire_by"),
                    "short_url": subscription.get("short_url", ""),
                    "has_scheduled_changes": subscription.get("has_scheduled_changes", False),
                    "source": subscription.get("source", "api"),
                    "offer_id": subscription.get("offer_id", ""),
                    "notes": subscription.get("notes", []),  # Ensure it's stored as JSON
                }
            )

        return f"Successfully updated {len(subscriptions)} subscriptions!"

    except requests.exceptions.RequestException as e:
        return f"Request error: {str(e)}"

    except Exception as e:
        return f"An unexpected error occurred: {str(e)}"

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from .models import Subscription, Plan, Subscription2
from .serializers import SubscriptionSerializer, PlanSerializer, Subscription2Serializer
from rest_framework.exceptions import NotFound

class SubscriptionDetailView(APIView):
    def get(self, request, subscription_id=None, format=None):
        tenant_id = request.headers.get('X-Tenant-Id')

        if tenant_id:
            try:
                subscription = Subscription.objects.get(tenant= tenant_id)
                serializer = SubscriptionSerializer(subscription)
                return Response(serializer.data)
            except Subscription.DoesNotExist:
                raise NotFound(detail="Subscription not found", code=404)
        else:
            subscriptions = Subscription.objects.all()
            serializer = SubscriptionSerializer(subscriptions, many=True)
            return Response(serializer.data)

    def delete(self, request, subscription_id, format=None):
        try:
            subscription = Subscription.objects.get(id=subscription_id)
        except Subscription.DoesNotExist:
            raise NotFound(detail="Subscription not found", code=404)
        
        subscription.delete()
        return Response({"message": "Subscription deleted successfully"}, status=status.HTTP_204_NO_CONTENT)

class PlanDetailView(APIView):
    def get(self, request, plan_id=None, format=None):
        if plan_id:
            try:
                plan = Plan.objects.get(id=plan_id)
                serializer = PlanSerializer(plan)
                return Response(serializer.data)
            except Plan.DoesNotExist:
                raise NotFound(detail="Plan not found", code=404)
        else:
            plans = Plan.objects.all()
            serializer = PlanSerializer(plans, many=True)
            return Response(serializer.data)

    def delete(self, request, plan_id, format=None):
        try:
            plan = Plan.objects.get(id=plan_id)
        except Plan.DoesNotExist:
            raise NotFound(detail="Plan not found", code=404)
        

        plan.delete()
        return Response({"message": "Plan deleted successfully"}, status=status.HTTP_204_NO_CONTENT)

@csrf_exempt
def get_subscription(request):
    try:
        tenant_id = request.headers.get('X-Tenant-Id')
        subscription = Subscription2.objects.filter(tenant = tenant_id).first()
        serializer = Subscription2Serializer(subscription)
        sub_data = serializer.data
        id = sub_data['id']
        response = requests.get(f"https://api.razorpay.com/v1/subscriptions/{id}", auth=(API_KEY_ID, API_KEY_SECRET))
        response_json = response.json()
        plan_id = response_json['plan_id']
        plan = Plan.objects.get(id = plan_id)
        plan_name = plan.name
        start = response_json['start_at'] or response_json['created_at']
        next = response_json['charge_at']
        days_rem = 87
        history = sub_data['past_payments']
        return JsonResponse({'success': True, 'data': {'currentPlan': plan_name, 'startDate': unix_to_datetime(start), 'nextBillingDate': unix_to_datetime(next), 'daysRemaining': days_rem, 'paymentHistory': history}})

    except Subscription.DoesNotExist:
        raise NotFound(detail="Subscription not found", code=404)
    except Exception as e:
        print("Exception: ", e)

@csrf_exempt
def webhook(request):
    try:
        body_unicode = request.body.decode('utf-8')
        body_data = json.loads(body_unicode)

        event = body_data['event']
        print("Received event: ", event)

        return JsonResponse({"status": "success", "message": "Received"}, status=200)
    except json.JSONDecodeError:
        print("Invalid JSON received:\n", request.body)
        return JsonResponse({"status": "error", "message": "Invalid JSON"}, status=400)
